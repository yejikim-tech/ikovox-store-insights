import assert from 'node:assert/strict';
import fs from 'node:fs';
import {sourceProducts,renderChannelAudit} from '../dist/channel-audit.js';
import {revenueBreakdown} from '../dist/revenue-parts.js';
import {dateRange} from '../dist/weekly-view.js';
import {posComparison} from '../dist/pos-comparison.js';
const read=p=>JSON.parse(fs.readFileSync(new URL('../'+p,import.meta.url)));
const a=read('dist/analysis-data.json'),l=read('dist/data.json'),c={...read('dist/channel-data.json'),direct:read('dist/direct-delivery.json')},h=read('reconciliations/h1-direct-review.json');
const expected=[65650800,62361000,85717800,110274580,115202400,88863700,77599500,78186600,86102900,100590400,4381100];
assert.equal(l.daily.length,306);assert.equal(new Set(l.daily.map(r=>r.date)).size,306);
assert.deepEqual(l.daily.map(r=>r.date),dateRange('2026-01-01','2026-11-02'));
assert.equal(c.direct.daily.length,243);
assert.equal(h.baeminHeader-h.baeminMerchantDiscountCorrections-h.baeminPartialRefunds,h.baeminNet);
assert.equal(h.baeminNet,12271000);assert.equal(h.coupangNet,43866200);
const products=sourceProducts(a.products,c),productTotals=new Map();
for(const r of products)productTotals.set(r.date,(productTotals.get(r.date)||0)+r.sales);
for(const row of l.daily){
 const b=revenueBreakdown([row.date],{analysis:a,channels:c,ledger:l.daily});
 assert.equal(b.complete,true,row.date);assert.equal(b.difference,0,row.date);
 assert.equal(productTotals.get(row.date),row.sales,'Product amounts including unknown buckets reconcile on '+row.date);
}
for(let i=0;i<11;i++)assert.equal(l.daily.filter(r=>r.date.startsWith(`2026-${String(i+1).padStart(2,'0')}`)).reduce((s,r)=>s+r.sales,0),expected[i]);
assert.equal(l.daily.reduce((s,r)=>s+r.sales,0),874930780);
assert(!products.some(r=>r.date>='2026-01-01'&&r.date<='2026-08-31'&&(r.channel==='otter'||r.channel==='payhere'&&r.category==='배달앱')));
assert(a.products.some(r=>r.category==='배달앱'),'Raw POS originals are retained');
for(const r of c.direct.products){assert(Number.isSafeInteger(r.sales));assert(!('orderId' in r));assert(!('orderKey' in r));if(r.unallocated)assert(r.unknownQty);}
const html=renderChannelAudit(c,{won:String,esc:String,nf:String});assert(html.includes('일별 합계 반영 완료'));assert(!html.includes('전 채널 총매출표 누락'));assert(!html.includes('undefined'));assert(!html.includes('NaN'));
const year=posComparison('2026-01-01','2026-10-28',a);assert.equal(year.current.total,805683280);assert.equal(year.previous.total,782295840);
console.log('306 contiguous days, 11 monthly controls, daily product/channel totals, 243-day duplicate exclusion, refund/discount reconciliation and unchanged POS-only YoY verified.');

const closing=l.daily.find(r=>r.date==='2026-10-29');assert.equal(closing.sales,2157500);assert.equal(l.daily.filter(r=>r.date<'2026-10-29').reduce((s,r)=>s+r.sales,0),860597180);
const parts=revenueBreakdown(['2026-10-29'],{analysis:a,channels:c,ledger:l.daily});assert.equal(parts.parts.pos.value,1683200);assert.equal(parts.parts.delivery.value,448500);assert.equal(parts.parts.naver.value,25800);assert.equal(parts.difference,0);
assert.equal(c.products.filter(r=>r.date==='2026-10-29'&&r.channel==='otter').length,53);assert(!c.products.some(r=>r.date==='2026-10-29'&&r.unallocated));

for(const [date,pos,delivery,naver,total] of [['2026-10-30',2733200,495900,34000,3263100],['2026-10-31',4085900,386400,59600,4531900],['2026-11-01',2197400,672300,12400,2882100],['2026-11-02',1135000,364000,0,1499000]]){const x=revenueBreakdown([date],{analysis:a,channels:c,ledger:l.daily});assert.deepEqual([x.parts.pos.value,x.parts.delivery.value,x.parts.naver.value,x.total],[pos,delivery,naver,total]);assert.equal(x.difference,0);assert(!c.products.some(r=>r.date===date&&r.unallocated));}
assert.equal(l.daily.filter(r=>r.date<='2026-10-29').reduce((s,r)=>s+r.sales,0),862754680);
