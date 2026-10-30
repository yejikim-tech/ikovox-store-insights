"""Import browser-visible closing originals. Keep customer/order identifiers private."""
from pathlib import Path
from collections import defaultdict
import json,re,hashlib,csv
R=Path(__file__).resolve().parents[1];P=R.parent/'audit/private';DAY='2026-10-29'
read=lambda f:json.loads((R/'dist'/f).read_text())
def save(f,v):(R/'dist'/f).write_text(json.dumps(v,ensure_ascii=False,separators=(',',':')))
def num(s):return int(re.sub(r'[^0-9-]','',str(s)) or 0)
p=json.loads((P/'payhere-20261029-products-ui.json').read_text());assert '26.10.29 ~ 26.10.29' in p['body'] and len(p['rows'])==56
sid='payhere-ui-'+hashlib.sha256((P/'payhere-20261029-products-ui.json').read_bytes()).hexdigest()[:16]
items=[]
for r in p['rows']:
 assert len(r)==15 and r[2]=='2026.10.29'
 items.append(dict(date=DAY,category=r[0],name=r[1],unitPrice=num(r[3]),qty=num(r[6]),sold=None,gross=num(r[8]),sales=num(r[9]),discount=num(r[10]),points=num(r[11]),prepaid=num(r[12]),refund=num(r[13]),refundQty=num(r[14]),source=sid))
assert sum(r['sales'] for r in items)==1683200 and sum(r['gross'] for r in items)==1703700
assert sum(r['discount'] for r in items)==20500 and sum(r['refund'] for r in items)==11200
assert not any(r['category']=='배달앱' for r in items)
a=read('analysis-data.json');oldHistorical=[r for r in a['products'] if r['date']!=DAY];a['products']=oldHistorical+items
if DAY not in a['productCoverage']:a['productCoverage'].append(DAY)
a['productCoverage'].sort();a['partialProductDates']=[d for d in a['partialProductDates'] if d!=DAY]
tot={k:sum(r[k] for r in items) for k in ['qty','gross','sales','discount','points','prepaid','refund','refundQty']};tot.update(date=DAY,source=sid,partial=False)
a['dailyProductTotals']=[r for r in a['dailyProductTotals'] if r['date']!=DAY]+[tot];a['dailyProductTotals'].sort(key=lambda r:r['date'])
a['importSources']=[r for r in a['importSources'] if r['id']!=sid]+[dict(id=sid,label='페이히어 2026-10-29 상품별·일자별 관리자 원본',start=DAY,end=DAY,kind='products',records=len(items),days=1,declared=tot,note='10/30 관리자 일자별 전체 56행 및 전체합계 대조. 환불은 원본 별도 항목 유지.')]
a['importRevision']='2026-10-30-closing';save('analysis-data.json',a)
# Order money: subtotal plus signed merchant discount; partner discounts are not deducted again.
o=json.loads((P/'otter-20261029-ui.json').read_text());assert re.search(r'어제:\s*2026\. 10\. 29\.',o['body']) and '23의 1-23' in o['body'] and len(o['rows'])==23
details={r['key']:r for r in json.loads((P/'otter-20261029-structured.json').read_text())};assert len(details)==23
products=[];net=0;unknown=0;optionRows=[]
for r in o['rows']:
 assert '2026. 10. 29.' in r[0] and r[5]=='완료된 주문' and r[7]=='Paid'
 gross=num(r[11]);discount=-num(r[15]);value=gross-discount;net+=value
 x=details[r[1]];assert '#'+r[1] in x['text'];nodes=x['nodes'];parents=[];i=0
 while i<len(nodes):
  n=nodes[i]
  if n['tag']=='SPAN' and n['text'].isdigit():
   assert nodes[i+1]['tag']=='SPAN' and nodes[i+2]['tag']=='DIV'
   parents.append(dict(qty=num(n['text']),name=nodes[i+1]['text'].strip(),unit=num(nodes[i+2]['text']),options=[]));i+=3
  elif n['role']=='group':
   cs=n['children'];assert len(cs)%3==0
   for j in range(0,len(cs),3):parents[-1]['options'].append(dict(qty=num(cs[j]['text']),name=cs[j+1]['text'].strip(),unit=num(cs[j+2]['text'])))
   i+=1
  else:assert n['text']=='';i+=1
 weights=[v['qty']*(v['unit']+sum(t['qty']*t['unit'] for t in v['options'])) for v in parents]
 if sum(weights)!=gross or sum(v['qty'] for v in parents)!=num(r[10]):
  unknown+=value;products.append(dict(date=DAY,name='[오터] 상품 상세 미확인',category='상품 미확인',channel='otter',sales=value,qty=0,unknownQty=True,unallocated=True,source='otter-20261029-ui'));continue
 alloc=[discount*w//gross for w in weights]
 for j in sorted(range(len(weights)),key=lambda j:-(discount*weights[j]%gross))[:discount-sum(alloc)]:alloc[j]+=1
 for v,w,disc in zip(parents,weights,alloc):
  products.append(dict(date=DAY,name=v['name'],category='채널 미분류',channel='otter',sales=w-disc,qty=v['qty'],gross=w,discount=disc,refund=0,refundQty=0,points=0,prepaid=0,source='otter-20261029-ui'))
  for t in v['options']:optionRows.append(dict(date=DAY,product=v['name'],option=t['name'],qty=v['qty']*t['qty'],channel='otter'))
assert net==448500 and sum(r['sales'] for r in products)==net
# Naver: order accepted on 29th, auto-completed 30th. Same accepted-date basis as existing records.
n=json.loads((P/'naver-20261029-ui.json').read_text())['body'];assert '25,800원' in n and '26.10.29.(목) 오후 9:44 (주문접수)' in n and '픽업완료' in n and '완료' in n
navItems=[dict(name='드립백 커피',qty=1,sales=16000),dict(name='얼그레이 무화과 복숭아 케이크',qty=1,sales=9800)]
products += [dict(date=DAY,category='채널 미분류',channel='naver',gross=x['sales'],discount=0,refund=0,refundQty=0,points=0,prepaid=0,source='naver-20261029-ui',**x) for x in navItems]
ch=read('channel-data.json');ch['products']=[r for r in ch['products'] if r['date']!=DAY]+products;ch['daily']=[r for r in ch['daily'] if r['date']!=DAY]+[dict(date=DAY,otter=net,otterOrders=23,otterCancelled=0,otterUnallocated=unknown,naver=25800,naverOrders=1,naverCancelled=0)];ch['daily'].sort(key=lambda r:r['date']);ch['asOf']=DAY;ch['revision']='2026-10-30-closing'
for c in ch['coverage']:
 if c['channel'] in ['payhere','otter','naver']:c['end']=DAY
m=next(r for r in ch['months'] if r['month']=='2026-10');m.update(payhere=79082300,posDays=29,appliedDelivery=11947800,otter=11947800,naver=1765300,reconciledTotal=92795400);m['otterOrders']=sum(r['otterOrders'] for r in ch['daily'] if r['date'].startswith('2026-10'));m['naverOrders']=sum(r['naverOrders'] for r in ch['daily'] if r['date'].startswith('2026-10'));save('channel-data.json',ch)
b=read('data.json');before={r['date']:r for r in b['daily'] if r['date']!=DAY};total=1683200+net+25800;b['daily']=list(before.values())+[dict(date=DAY,sales=total,orders=None,weather='',promotion='',note='10/30 관리자 마감 원본 대조. 오터 23건 소계 451,500원에서 가맹점 할인 3,000원 반영. 네이버 29일 주문 1건 25,800원은 30일 자동 완료 확인, 접수일 기준 반영. POS 환불 11,200원은 원본 별도 표시.',revenueBasis='POS 실매출 + 오터 소계·가맹점 할인 + 네이버 완료 주문 접수일',reconciliation='daily-originals-verified')];b['daily'].sort(key=lambda r:r['date']);b['updated']='2026-10-30';save('data.json',b)
with (R/'dist/channel-monthly-audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['월','POS 원본','제외 POS 배달앱','적용 배달 순매출','네이버 완료액','통합 총매출','기준']);w.writerows([[r[k] for k in ['month','payhere','excludedPosDelivery','appliedDelivery','naver','reconciledTotal','status']] for r in ch['months']])
(R/'reconciliations/20261029-closing.json').write_text(json.dumps(dict(date=DAY,pos=1683200,delivery=net,naver=25800,total=total,posProducts=56,deliveryProducts=len(products)-2,deliveryUnknown=unknown,deliveryOptionSelections=sum(r['qty'] for r in optionRows),orders=dict(delivery=23,naver=1),posRefundSeparate=11200,netBasis='POS original net; Otter subtotal minus merchant discount; Naver accepted date, completed status verified next day',annual=sum(r['sales'] for r in b['daily'])),ensure_ascii=False,indent=2))
print(dict(total=total,pos=1683200,delivery=net,naver=25800,deliveryUnknown=unknown,deliveryProducts=len(products)-2,annual=sum(r['sales'] for r in b['daily'])))
