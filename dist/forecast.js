// Forecast only the combined store ledger. No POS fallback and no future training rows.
const DAY=86400000,date=s=>new Date(s+'T00:00:00Z'),iso=d=>d.toISOString().slice(0,10),add=(s,n)=>iso(new Date(+date(s)+n*DAY));
const dow=s=>date(s).getUTCDay(),sum=xs=>xs.reduce((a,b)=>a+b,0),mean=xs=>xs.length?sum(xs)/xs.length:null;
const quantile=(xs,p)=>{const a=[...xs].sort((a,b)=>a-b);if(!a.length)return null;const i=(a.length-1)*p,l=Math.floor(i);return a[l]+(a[Math.ceil(i)]-a[l])*(i-l)};
const median=xs=>quantile(xs,.5),clip=(x,l,h)=>Math.max(l,Math.min(h,x));
const days=(a,b)=>{const rs=[];for(let d=a;d<=b;d=add(d,1))rs.push(d);return rs};
export const weatherType=s=>/소나기|비|폭우/.test(s||'')?'rain':/폭염/.test(s||'')?'heat':/눈/.test(s||'')?'snow':/맑|해|구름|흐림/.test(s||'')?'normal':null;
export const forecastModels=[
  {id:'weekday28',label:'최근 4주 요일 평균',window:28,trend:false},
  {id:'weekday56',label:'최근 8주 요일 평균',window:56,trend:false},
  {id:'trend56',label:'최근 8주 요일 평균 + 최근 추세',window:56,trend:true}
];
export function fitForecast(rows,asof,config){
  const history=rows.filter(r=>r.date<=asof&&r.date>=add(asof,-config.window+1));
  const weekday=Array.from({length:7},(_,d)=>{const same=history.filter(r=>dow(r.date)===d),lo=quantile(same.map(r=>r.sales),.1),hi=quantile(same.map(r=>r.sales),.9);let weight=0,total=0;
    for(const r of same){const w=Math.pow(.5,(+date(asof)-date(r.date))/DAY/28);total+=clip(r.sales,lo,hi)*w;weight+=w}
    return {day:d,count:same.length,mean:weight?total/weight:null};
  });
  const ratios=(start,end)=>history.filter(r=>r.date>=start&&r.date<=end&&weekday[dow(r.date)].mean>0).map(r=>r.sales/weekday[dow(r.date)].mean);
  const recent=ratios(add(asof,-13),asof),previous=ratios(add(asof,-41),add(asof,-14));
  const rawTrend=recent.length>=10&&previous.length>=14&&median(previous)>0?median(recent)/median(previous):1;
  const trend=config.trend?clip(1+.5*(rawTrend-1),.8,1.2):1;
  const weatherGroups={normal:[],rain:[],heat:[],snow:[]};
  for(const r of rows.filter(r=>r.date<=asof&&r.date>=add(asof,-111))){const type=weatherType(r.weather),base=weekday[dow(r.date)].mean;if(type&&base>0)weatherGroups[type].push({date:r.date,ratio:r.sales/(base*trend)})}
  const weatherFactors={};
  const supported=rs=>rs.length>=8&&new Set(rs.map(r=>dow(r.date))).size>=4&&(+date(rs.at(-1).date)-date(rs[0].date))/DAY>=21;
  const weatherKnown=Object.values(weatherGroups).reduce((n,rs)=>n+rs.length,0);
  for(const type of ['rain','heat','snow'])if(weatherKnown>=28&&supported(weatherGroups.normal)&&supported(weatherGroups[type])&&median(weatherGroups.normal.map(r=>r.ratio))>0){
    // Shrink toward no adjustment. This is an observed association, not a causal estimate.
    weatherFactors[type]=clip(1+.5*(median(weatherGroups[type].map(r=>r.ratio))/median(weatherGroups.normal.map(r=>r.ratio))-1),.8,1.2);
  }
  return {weekday,trend,rawTrend,weatherFactors,weatherKnown,weatherNormal:weatherGroups.normal.length,
    predict:(day,weather=null)=>weekday[dow(day)].mean===null?null:Math.max(0,weekday[dow(day)].mean*trend*(weatherFactors[weatherType(weather)||weather]??1))};
}
function evaluate(rows,origins,horizon,config,baseline=false){
  const map=new Map(rows.map(r=>[r.date,r])),results=[];
  for(const origin of origins){const targets=days(add(origin,1),add(origin,horizon));if(targets.some(d=>!map.has(d)))continue;
    const training=rows.filter(r=>r.date<=origin),fit=fitForecast(training,origin,config);
    if(fit.weekday.some(x=>x.count<3))continue;
    const monthRows=training.filter(r=>r.date.slice(0,7)===origin.slice(0,7));
    const prediction=baseline?mean(monthRows.map(r=>r.sales))*horizon:sum(targets.map(d=>fit.predict(d)));
    const actual=sum(targets.map(d=>map.get(d).sales));results.push({origin,prediction,actual,error:actual-prediction});
  }
  return {results,wape:results.length&&sum(results.map(r=>r.actual))>0?sum(results.map(r=>Math.abs(r.error)))/sum(results.map(r=>r.actual)):null};
}
export function forecastMonth(input,month,today,weatherPlan={}){
  const first=month+'-01',end=iso(new Date(Date.UTC(+month.slice(0,4),+month.slice(5),0)));
  const unique=new Map();for(const r of input)if(r.date<today&&Number.isFinite(r.sales)&&r.sales>=0)unique.set(r.date,r);
  const rows=[...unique.values()].sort((a,b)=>a.date.localeCompare(b.date)),inMonth=rows.filter(r=>r.date>=first&&r.date<=end),asof=inMonth.at(-1)?.date;
  if(!asof)return {status:'missing',reason:'선택 월의 마감 매출이 필요합니다.'};
  const map=new Map(rows.map(r=>[r.date,r])),elapsed=days(first,asof),actual=sum(inMonth.map(r=>r.sales));
  if(elapsed.some(d=>!map.has(d)))return {status:'missing',reason:'월초부터 기준일까지 누락된 매출을 먼저 확인해 주세요.'};
  if(asof===end)return {status:'closed',asof,actual,total:actual,remaining:[]};
  if(rows.length<42)return {status:'missing',reason:'요일·추세 검증에는 최소 6주 매출이 필요합니다.'};
  const targets=days(add(asof,1),end),horizon=targets.length;
  const eligible=rows.filter((r,i)=>i>=41&&r.date<=add(asof,-horizon)&&r.date>=add(asof,-84)).map(r=>r.date);
  const evaluationCount=Math.min(21,Math.floor(eligible.length/3)),evalOrigins=evaluationCount?eligible.slice(-evaluationCount):[];
  const selectionOrigins=evalOrigins.length?eligible.filter(d=>add(d,horizon)<evalOrigins[0]):[];
  const scores=forecastModels.map(model=>({model,...evaluate(rows,selectionOrigins,horizon,model)}));
  const valid=scores.filter(s=>s.results.length>=10&&s.wape!==null).sort((a,b)=>a.wape-b.wape);
  const selected=valid[0]?.model||forecastModels[1],fit=fitForecast(rows,asof,selected);
  if(fit.weekday.some(x=>x.count<3))return {status:'missing',reason:'각 요일의 매출이 최소 3번씩 필요합니다.'};
  const validation=evaluate(rows,evalOrigins,horizon,selected),baseline=evaluate(rows,evalOrigins,horizon,selected,true);
  const remaining=targets.map(d=>{const weather=weatherPlan[d]||'',factor=fit.weatherFactors[weather]??1;return {date:d,day:dow(d),weekdayBase:fit.weekday[dow(d)].mean,trend:fit.trend,weather,weatherFactor:factor,weatherApplied:Object.hasOwn(fit.weatherFactors,weather),sales:fit.predict(d,weather)}});
  const predicted=sum(remaining.map(r=>r.sales)),errors=validation.results.map(r=>r.error);
  const weatherScenario=remaining.some(r=>r.weatherApplied),calibrated=errors.length>=10&&!weatherScenario,lowError=calibrated?Math.min(0,quantile(errors,.1)):null,highError=calibrated?Math.max(0,quantile(errors,.9)):null;
  return {status:'forecast',asof,actual,total:actual+predicted,predicted,remaining,model:selected,selectionScores:scores.map(s=>({id:s.model.id,label:s.model.label,wape:s.wape,count:s.results.length})),
    selectionCount:selectionOrigins.length,validationCount:errors.length,wape:validation.wape,baselineWape:baseline.wape,
    low:calibrated?actual+Math.max(0,predicted+lowError):null,high:calibrated?actual+Math.max(0,predicted+highError):null,
    trend:fit.trend,rawTrend:fit.rawTrend,weekday:fit.weekday,weatherKnown:fit.weatherKnown,weatherNormal:fit.weatherNormal,weatherFactors:fit.weatherFactors,
    evaluationStart:validation.results[0]?.origin,evaluationEnd:validation.results.at(-1)?.origin,horizon,
    provisional:!valid.length||!calibrated,weatherScenario,
    stale:asof<add(today,-1),note:'확인한 채널 원본의 통합 매출 기준 조건부 예측. 행사·공휴일·품절·영업시간 변경은 오차에 영향을 줄 수 있습니다.'};
}
