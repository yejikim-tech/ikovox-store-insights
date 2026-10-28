"""Read authorized local exports, publish aggregates only. No customer/order identifiers leave this process.
Otter merchant product basis = subtotal + merchant discount, excluding delivery/settlement charges.
Missing item detail and changed-order line mismatches remain explicitly unallocated.
"""
import collections,csv,datetime,decimal,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[1]
HOME=pathlib.Path.home(); DL=HOME/'Downloads'
END='2026-10-27'
def num(v):return int(decimal.Decimal(str(v or 0).replace(',','')).quantize(decimal.Decimal('1')))
def read(name):return list(csv.DictReader((DL/name).open(encoding='utf-8-sig')))
def dt(s):
 p=s.split('.');return f'{int(p[0]):04}-{int(p[1]):02}-{int(p[2]):02}'
def key(r):return tuple(r.get(k,'') for k in ['주문 번호','Fulfilled','채널','브랜드','지점 '])
def allocate(total,weights):
 if not weights or sum(weights)<=0:return []
 values=[total*w//sum(weights) for w in weights]
 for i in sorted(range(len(weights)),key=lambda i:-(total*weights[i]%sum(weights)))[:total-sum(values)]:values[i]+=1
 return values
pos=json.loads((ROOT/'dist/analysis-data.json').read_text());ledger=json.loads((ROOT/'dist/data.json').read_text())
nav=json.loads((ROOT.parent/'audit/private/naver-orders.json').read_text())
if isinstance(nav,dict):
 print('Naver schema',list(nav));nav=nav.get('orders',[])
assert len({r['key'] for r in nav})==len(nav)
orders={key(r):r for r in read('주문내역-1793169547869.csv') if dt(r['Fulfilled'])<=END}
lines=collections.defaultdict(list);line_seen=set()
for r in read('주문내역-1793169681279.csv'):
 k=(key(r),r['주문 세부 항목 ID'])
 if k in line_seen:continue
 line_seen.add(k);lines[key(r)].append(r)
products=[];daily=collections.defaultdict(lambda:dict(otter=0,otterOrders=0,otterCancelled=0,otterUnallocated=0,naver=0,naverOrders=0,naverCancelled=0))
exceptions=collections.Counter();cancelled=collections.Counter()
def product(date,name,channel,sales,qty,gross,discount=0,reason=None):
 products.append(dict(date=date,name=name.strip(),category='채널 미분류' if not reason else '상품 미확인',channel=channel,sales=sales,qty=qty,gross=gross,discount=discount,refund=0,refundQty=0,points=0,prepaid=0,source='channel-export-20261028',unallocated=bool(reason),reason=reason))
for k,o in orders.items():
 d=dt(o['Fulfilled']);day=daily[d]
 if o['주문상태']!='완료된 주문':day['otterCancelled']+=1;continue
 gross=num(o['소계 ']);discount=-num(o['할인 ']);net=gross-discount
 day['otter']+=net;day['otterOrders']+=1
 rs=lines.get(k,[]);parents=[r for r in rs if not r['Parent Order Line Item IDs']]
 reason=None
 if not rs:reason='상품 상세 미제공'
 elif sum(num(r['메뉴소계']) for r in rs)!=gross:reason='변경·부분취소 상품 대조 필요'
 else:
  ids={r['주문 세부 항목 ID'] for r in parents}
  if any(r['Parent Order Line Item IDs'] and r['Parent Order Line Item IDs'] not in ids for r in rs):reason='옵션 부모 연결 미확인'
  if not parents:reason='상품 연결 미확인'
 if reason:
  exceptions[reason]+=1;day['otterUnallocated']+=net
  product(d,'[오터] '+reason,'otter',net,None,gross,discount,reason);continue
 weights=[];quantities=[]
 for p in parents:
  pid=p['주문 세부 항목 ID'];amount=num(p['메뉴소계'])+sum(num(r['메뉴소계']) for r in rs if r['Parent Order Line Item IDs']==pid)
  weights.append(amount);unit=num(p['메뉴 할인 가격']);subtotal=num(p['메뉴소계'])
  quantities.append(subtotal//unit if unit>0 and subtotal%unit==0 else None)
 shares=allocate(discount,weights)
 if len(shares)!=len(parents):
  shares=[0]*len(parents)
  assert discount==0
 for p,g,q,disc in zip(parents,weights,quantities,shares):product(d,p['주문 완료 메뉴'],'otter',g-disc,q,g,disc)
for o in nav:
 d=o['date']
 if d>END:continue
 day=daily[d]
 if o['status']!='완료':day['naverCancelled']+=1;continue
 amount=o['money']['실결제금액'];assert sum(i['amount'] for i in o['items'])==amount
 day['naver']+=amount;day['naverOrders']+=1
 for i in o['items']:product(d,i['name'],'naver',i['amount'],i['qty'],i['amount'])
# Aggregate only date/product/channel, discard source identifiers.
groups={}
for r in products:
 k=(r['date'],r['name'],r['channel'],r['reason'])
 if k not in groups:groups[k]={**r,'qty':0,'unknownQty':False}
 g=groups[k]
 if r['qty'] is None:g['unknownQty']=True
 else:g['qty']+=r['qty']
 if g is not r:
  # First row was copied with its amounts; accumulate only later occurrences.
  if g.pop('_initialized',False):
   for f in ['sales','gross','discount']:g[f]+=r[f]
 g['_initialized']=True
for r in groups.values():r.pop('_initialized',None)
products=list(groups.values())
months=[]
for month in [f'2026-{m:02}' for m in range(1,11)]:
 pr=[r for r in pos['products'] if r['date'].startswith(month) and r['date']<=END]
 days=sorted({r['date'] for r in pr}); dr=[(d,v) for d,v in daily.items() if d.startswith(month)]
 old=[r for r in ledger['daily'] if r['date'].startswith(month)]
 months.append(dict(month=month,payhere=sum(num(r['sales']) for r in pr),posDays=len(days),posDelivery=sum(num(r['sales']) for r in pr if r['category']=='배달앱'),otter=sum(v['otter'] for d,v in dr) if any(v['otterOrders'] for d,v in dr) else None,otterOrders=sum(v['otterOrders'] for d,v in dr),otterUnallocated=sum(v['otterUnallocated'] for d,v in dr) if any(v['otterOrders'] for d,v in dr) else None,naver=sum(v['naver'] for d,v in dr) if month>='2026-03' else None,naverOrders=sum(v['naverOrders'] for d,v in dr),legacy=sum(r['sales'] for r in old) if old else None,legacyDays=len(old),status='중복·기준일 대조 중' if month>='2026-07' else '총매출표 누락 · 채널 완전성 확인 필요'))
output=dict(revision='2026-10-28-channel-audit',asOf=END,products=products,daily=[dict(date=d,**v) for d,v in sorted(daily.items())],months=months,exceptions=dict(exceptions),coverage=[dict(channel='payhere',start='2025-01-01',end='2026-10-28',note='2025년 전체·2026년 연초 POS 상품 원본 확보. 10/28 잠정. 배달앱 포함 구간 중복 대조 필요.'),dict(channel='otter',start='2026-07-21',end=END,itemStart='2026-08-20',note='연간 조회 주문 원본의 첫 관측 7/21. 이전 기간 연동·영업 여부 미확인. 8/20 이전 상세와 변경 주문은 상품 미확인으로 보존.'),dict(channel='naver',start='2026-03-20',end=END,note='2025/1/1~2026/10/27 전체 상태 조회 926건. 완료 873건 상품액=실결제액. 이전 기간 연동·영업 여부 미확인.')],policy='채널 원본 수집분입니다. POS 배달앱과 오터 중복 및 총매출표 차이 미해결. 합산은 잠정 원본 합계이며 확정 매장 총매출이 아닙니다. 오터 배송·수수료 포함 합계 대신 소계+가맹점 할인 사용. 주문 할인은 상품·유료옵션 금액 비율로 원 단위 배분. 취소 주문 제외. 상품 불일치·상세 누락 주문은 미확인으로 보존.')
(ROOT/'dist/channel-data.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')))
(ROOT/'reconciliations/full-year-audit.json').write_text(json.dumps({k:v for k,v in output.items() if k not in ['products','daily']},ensure_ascii=False,indent=2))
print(json.dumps(dict(rows=len(products),exceptions=dict(exceptions),months=months),ensure_ascii=False))
