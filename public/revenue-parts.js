// Keep independently collected channel amounts separate from the saved headline.
// A mismatch is evidence to review, never a residual assigned to a channel.
export function revenueBreakdown(dates,{analysis,channels,ledger=[]}){
  const ds=[...new Set(dates)],posDays=new Set(analysis?.productCoverage||[]),pos=new Map(),daily=new Map((channels?.daily||[]).map(r=>[r.date,r])),direct=new Map((channels?.direct?.daily||[]).map(r=>[r.date,r]));
  for(const r of analysis?.products||[]){if(r.channel&&r.channel!=='payhere')continue;if(direct.has(r.date)&&r.category==='배달앱')continue;pos.set(r.date,(pos.get(r.date)||0)+r.sales)}
  const covered=(key,d)=>{const c=channels?.coverage?.find(c=>c.channel===key);return !!c&&d>=c.start&&d<=c.end};
  const parts={pos:{label:'POS',value:0,count:0},naver:{label:'네이버',value:0,count:0},delivery:{label:'배달',value:0,count:0}};
  for(const d of ds){const dr=direct.get(d),r=daily.get(d);
    if(dr||posDays.has(d)){parts.pos.value+=dr?dr.payhereStore:pos.get(d)||0;parts.pos.count++}
    if(dr||covered('naver',d)){parts.naver.value+=dr?dr.naver:r?.naver||0;parts.naver.count++}
    if(dr||covered('otter',d)){parts.delivery.value+=dr?dr.baemin+dr.coupang:r?.otter||0;parts.delivery.count++}
  }
  const rows=ledger.filter(r=>ds.includes(r.date)),headline=rows.length?rows.reduce((s,r)=>s+r.sales,0):null,complete=ds.length>0&&Object.values(parts).every(p=>p.count===ds.length),total=complete?Object.values(parts).reduce((s,p)=>s+p.value,0):null;
  return {parts,days:ds.length,complete,total,headline,headlineComplete:rows.length===ds.length&&ds.length>0,difference:complete&&rows.length===ds.length?total-headline:null};
}
export function renderRevenueBreakdown(b,{won},compact=false){
  return `<div class="revenue-parts ${compact?'compact':''}" aria-label="POS 네이버 배달 매출 구성">${Object.entries(b.parts).map(([key,p])=>`<div data-revenue-part="${key}"><span>${p.label}</span><b>${p.count?won(p.value):'미확인'}</b>${p.count<b.days?`<small>${p.count}/${b.days}일 확인</small>`:''}</div>`).join('')}<p>${b.difference!==null?(b.difference===0?'원본 채널 합계 = 표시 총매출':`원본 합계 − 표시 총매출: ${b.difference>0?'+':'−'}${won(Math.abs(b.difference))} · 대조 중`):'채널별 확인 원본 · 미수집일은 0원으로 보지 않습니다.'}</p></div>`;
}
