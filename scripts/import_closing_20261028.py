from pathlib import Path
from collections import defaultdict
import json,csv,hashlib
from openpyxl import load_workbook
R=Path('/Users/kimyeji/Documents/ChatGPT/이코복스/ecobox-pm');D=Path.home()/'Downloads';day='2026-10-28'
def read(n):return json.loads((R/'dist'/n).read_text())
def save(n,x):(R/'dist'/n).write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
def num(v):return round(float(str(v or 0).replace(',','')))
a=read('analysis-data.json');p=next(p for p in D.glob('상품 분석_상품별 조회(일자별)*2026-10-28.xlsx') if p.name.endswith('_2026-10-28.xlsx'));rs=list(load_workbook(p,read_only=True,data_only=True).active.values);sid='xlsx-'+hashlib.sha256(p.read_bytes()).hexdigest()[:16];items=[];tot=None
metrics=['unitPrice','qty','sold','gross','sales','discount','points','prepaid','refund','refundQty']
for i,r in enumerate(rs[7:],8):
 v=dict(zip(metrics,r[3:]))
 if str(r[0]).startswith('일자별 합계') and r[2]==day:tot=dict(date=day,source=sid,partial=False,**v)
 elif r[1] and r[2]==day:items.append(dict(date=day,category=r[0],name=r[1],source=sid,sourceRow=i,**v))
assert tot and sum(r['sales'] or 0 for r in items)==tot['sales']==1825000
for k in ['qty','gross','sales','discount','refund']:assert sum(r[k] or 0 for r in items)==(tot[k] or 0)
a['products']=[r for r in a['products'] if r['date']!=day]+items;a['dailyProductTotals']=[r for r in a['dailyProductTotals'] if r['date']!=day]+[tot];a['partialProductDates']=[d for d in a['partialProductDates'] if d!=day];a['importSources'].append(dict(id=sid,label=p.name,start=day,end=day,kind='products',records=len(items),days=1,declared=tot,note='28일 잠정 상품 행을 마감 원본으로 대체'));save('analysis-data.json',a)
rows=list(csv.DictReader((D/'주문내역-1793254288067.csv').open(encoding='utf-8-sig')));groups=defaultdict(list)
for r in rows:assert r['Fulfilled'].startswith('2026.10.28') or r['Fulfilled'].startswith('2026. 10. 28'),r['Fulfilled'];groups[r['주문 번호']].append(r)
products=[];net=0;unknown=0
for rs in groups.values():
 o=rs[0];assert o['주문상태']=='완료된 주문';gross=num(o['소계 ']);disc=-num(o['할인 ']);value=gross-disc;net+=value;parents=[r for r in rs if not r['Parent Order Line Item IDs']];weights=[num(p['메뉴소계'])+sum(num(r['메뉴소계']) for r in rs if r['Parent Order Line Item IDs']==p['주문 세부 항목 ID']) for p in parents]
 if not parents or sum(weights)!=gross:
  parents=[dict(주문완료메뉴='[오터] 상품 상세 미확인')];weights=[gross];unknown+=value
 alloc=[disc*w//sum(weights) for w in weights]
 for i in sorted(range(len(weights)),key=lambda i:-(disc*weights[i]%sum(weights)))[:disc-sum(alloc)]:alloc[i]+=1
 for p,w,discount in zip(parents,weights,alloc):
  unit=num(p.get('메뉴 할인 가격'));sub=num(p.get('메뉴소계'));qty=sub//unit if unit>0 and sub%unit==0 else None
  products.append(dict(date=day,name=p.get('주문 완료 메뉴',p.get('주문완료메뉴')),category='채널 미분류' if qty is not None else '상품 미확인',channel='otter',sales=w-discount,qty=qty or 0,gross=w,discount=discount,refund=0,refundQty=0,points=0,prepaid=0,source='otter-20261028-final',unallocated=qty is None,unknownQty=qty is None))
assert len(groups)==18 and net==317000 and sum(r['sales'] for r in products)==net
ch=read('channel-data.json');ch['products']=[r for r in ch['products'] if r['date']!=day]+products;ch['daily']=[r for r in ch['daily'] if r['date']!=day]+[dict(date=day,otter=net,otterOrders=18,otterCancelled=0,otterUnallocated=unknown,naver=0,naverOrders=0,naverCancelled=0)];ch['asOf']=day
for c in ch['coverage']:c['end']=day
save('channel-data.json',ch)
b=read('data.json');b['daily']=[r for r in b['daily'] if r['date']!=day]+[dict(date=day,sales=1825000+net,orders=144,weather='',promotion='',note='10/29 조회 마감 원본. 네이버 전체상태 10/28~29 0건. POS 환불은 원본 별도 표시, 오터 가맹점 할인 5,000원 반영.',revenueBasis='POS 실매출 + 오터 소계·가맹점 할인 + 네이버 완료액',reconciliation='daily-originals-verified')];b['daily'].sort(key=lambda r:r['date']);b['updated']='2026-10-29';save('data.json',b)
print(dict(pos=1825000,delivery=net,naver=0,total=1825000+net,posProducts=len(items),deliveryProducts=len(products)))
