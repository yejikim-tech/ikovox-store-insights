import assert from 'node:assert/strict';
import fs from 'node:fs';
import {sourceProducts,renderChannelAudit} from '../dist/channel-audit.js';
import {revenueBreakdown} from '../dist/revenue-parts.js';
import {dateRange} from '../dist/weekly-view.js';
import {posComparison} from '../dist/pos-comparison.js';
const read=p=>JSON.parse(fs.readFileSync(new URL('../'+p,import.meta.url)));
const a=read('dist/analysis-data.json'),l=read('dist/data.json'),c={...read('dist/channel-data.json'),direct:read('dist/direct-delivery.json')},h=read('reconciliations/h1-direct-review.json');
const expected=[65650800,62361000,85717800,110274580,115202400,88863700,77599500,78186600,86102900,90637900];
assert.equal(l.daily.length,301);assert.equal(new Set(l.daily.map(r=>r.date)).size,301);
assert.deepEqual(l.daily.map(r=>r.date),dateRange('2026-01-01','2026-10-28'));
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
for(let i=0;i<10;i++)assert.equal(l.daily.filter(r=>r.date.startsWith(`2026-${String(i+1).padStart(2,'0')}`)).reduce((s,r)=>s+r.sales,0),expected[i]);
assert.equal(l.daily.reduce((s,r)=>s+r.sales,0),860597180);
assert(!products.some(r=>r.date>='2026-01-01'&&r.date<='2026-08-31'&&(r.channel==='otter'||r.channel==='payhere'&&r.category==='배달앱')));
assert(a.products.some(r=>r.category==='배달앱'),'Raw POS originals are retained');
for(const r of c.direct.products){assert(Number.isSafeInteger(r.sales));assert(!('orderId' in r));assert(!('orderKey' in r));if(r.unallocated)assert(r.unknownQty);}
const html=renderChannelAudit(c,{won:String,esc:String,nf:String});assert(html.includes('일별 합계 반영 완료'));assert(!html.includes('전 채널 총매출표 누락'));assert(!html.includes('undefined'));assert(!html.includes('NaN'));
const year=posComparison('2026-01-01','2026-10-28',a);assert.equal(year.current.total,805683280);assert.equal(year.previous.total,782295840);
console.log('301 contiguous days, 10 independent monthly controls, daily product/channel totals, 243-day duplicate exclusion, refund/discount reconciliation and unchanged POS-only YoY verified.');
