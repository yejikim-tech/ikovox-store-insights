import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createWeatherView} from '../public/weather-view.js';
import {createSalesView} from '../public/sales-view.js';
const read=p=>JSON.parse(fs.readFileSync(new URL('../'+p,import.meta.url)));
const w=read('public/weather-data.json'),b=read('public/data.json'),a=read('public/analysis-data.json');
const expectedDays=Math.round((new Date(w.asOf)-new Date('2025-01-01'))/86400000)+1;const nextDate=new Date(new Date(w.asOf).getTime()+86400000).toISOString().slice(0,10);assert.equal(w.daily.length,expectedDays);assert.equal(w.daily[0].date,'2025-01-01');assert.equal(w.daily.at(-1).date,w.asOf);assert.equal(w.asOf,b.daily.at(-1).date);assert.equal(w.timezone,'Asia/Seoul');
assert.equal(new Set(w.daily.map(x=>x.date)).size,expectedDays);
for(const r of w.daily){assert.ok(r.tempMin<=r.tempMean&&r.tempMean<=r.tempMax);assert.ok(r.windMax>=0);assert.ok(r.gustMax>=0);if(r.precipitationRaw==='-')assert.equal(r.precipitation,null);}
assert.ok(w.daily.some(r=>r.precipitation===0),'Numeric zero retained separately from a dash');assert.ok(w.daily.some(r=>r.condition==='눈'));assert.ok(w.daily.some(r=>r.condition==='비'));
let exported;const view=createWeatherView(()=>w,{esc:String,won:n=>'₩'+n,download:(...x)=>exported=x,csvCell:v=>'"'+String(v).replaceAll('"','""')+'"'});
assert.equal(view.at(nextDate),null,'Partial current day must not be presented as finalized historical weather');
assert.ok(view.card('2026-10-27','매장 비 메모').includes('매장 비 메모'));assert.ok(view.card('2026-10-27').includes('— (원본 -)'));assert.ok(view.card(nextDate).includes('아직 없습니다'));
view.table('2026-08-01','2026-08-31',b.daily);view.exportCurrent();assert.ok(exported[1].includes('최대풍속'));assert.ok(exported[1].includes('2026-08-31'));assert.equal(exported[1].split('\r\n').length,32);
view.table('2026-10-01','2026-10-31',b.daily);view.exportCurrent();assert.equal(exported[1].split('\r\n').length,32);assert.ok(exported[1].includes('2026-10-31'));
const before=JSON.stringify(b);const sum=(rs,k)=>rs.reduce((s,r)=>s+(r[k]??0),0),iso=d=>d.toISOString().slice(0,10),date=s=>new Date(s+'T00:00:00Z');
globalThis.location={hash:'#dashboard?from=2026-10-27&to=2026-10-27&tab=trend'};
const sales=createSalesView({getAnalysis:()=>a,getWeather:()=>w,getRows:()=>b.daily,read:(k,d)=>d,today:'2026-10-28',sum,date,iso,add:(s,n)=>iso(new Date(+date(s)+n*86400000)),esc:String,nf:String,won:n=>'₩'+n});
assert.ok(sales.render().includes('테라스·루프탑 날씨'));assert.equal(JSON.stringify(b),before,'Original revenue and manual weather are immutable');
console.log(expectedDays+' historical dates, source units, dash versus zero, snow/rain, current-day exclusion, combined export, date detail and immutable sales/manual weather verified.');

assert.equal(view.at('2026-10-29').condition,'비');assert.equal(view.at('2026-10-29').precipitation,3);assert.equal(view.at('2026-10-29').tempMin,4.2);assert.equal(view.at('2026-10-29').tempMax,10.2);
