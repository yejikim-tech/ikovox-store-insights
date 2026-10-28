"""Replace July/Aug transition ledger with direct platform originals; publish aggregates only."""
from pathlib import Path
from collections import defaultdict,Counter
from openpyxl import load_workbook
import csv,json,re,hashlib,warnings
warnings.filterwarnings('ignore',category=UserWarning)
ROOT=Path(__file__).resolve().parents[1];PRIVATE=ROOT.parent/'audit/private';DL=Path.home()/'Downloads'
def num(v):return round(float(str(v or 0).replace(',','')))
def allocate(total,weights):
 if sum(weights)<=0:return [0]*len(weights)
 out=[total*w//sum(weights) for w in weights]
 for i in sorted(range(len(weights)),key=lambda i:-(total*weights[i]%sum(weights)))[:total-sum(out)]:out[i]+=1
 return out
# IDs exist only in process memory; joins require exact platform order identifiers.
otter=defaultdict(list)
for r in csv.DictReader((DL/'주문내역-1793169681279.csv').open(encoding='utf-8-sig')):
 if r['주문상태']=='완료된 주문':otter[r['주문 번호']].append(r)
def otter_items(oid):
 rs=otter.get(oid,[])
 if not rs:return None
 parents=[r for r in rs if not r['Parent Order Line Item IDs']]
 if sum(num(r['메뉴소계']) for r in rs)!=num(rs[0]['소계 ']):return None
 ids={p['주문 세부 항목 ID'] for p in parents}
 if not parents or any(r['Parent Order Line Item IDs'] and r['Parent Order Line Item IDs'] not in ids for r in rs):return None
 result=[]
 for p in parents:
  unit=num(p['메뉴 할인 가격']);subtotal=num(p['메뉴소계']);qty=subtotal//unit if unit>0 and subtotal%unit==0 else None
  amount=subtotal+sum(num(r['메뉴소계']) for r in rs if r['Parent Order Line Item IDs']==p['주문 세부 항목 ID'])
  result.append(dict(name=p['주문 완료 메뉴'].strip(),qty=qty,amount=amount))
 return result
orders=[];meta=[]
for store,filename in [('커피','baemin-coffee-jul-aug-pages.json'),('젤라또','baemin-gelato-jul-aug-completed.json')]:
 source=json.loads((PRIVATE/filename).read_text());cards=[c for p in source for c in p['cards']] if isinstance(source,list) else source['cards']
 seen=set()
 for c in cards:
  oid=re.search(r'주문번호\s*(?:배달완료|주문취소)?\s*([A-Z0-9]+)',c).group(1);assert oid not in seen;seen.add(oid)
  dt='-'.join(re.search(r'주문시각\s*(\d{4})\.\s*(\d{2})\.\s*(\d{2})',c).groups())
  assert '2026-07-01'<=dt<='2026-08-31'
  payment=num(re.search(r'결제금액\s*(?:부분취소\s*)?([\d,]+)\s*원',c.split('접기')[0]).group(1))
  items=otter_items(oid);basis='직접 주문번호와 오터 상품 연결' if items else None
  if not items and '주문 추가 정보 보기' in c:
   seg=c.split('주문 추가 정보 보기',1)[1].split('총 결제금액')[0].splitlines();found=[]
   for i,line in enumerate(seg):
    m=re.fullmatch(r'(.*?)(\d+)개',line.strip())
    if m and i+1<len(seg) and re.fullmatch(r'[\d,]+원',seg[i+1].strip()):found.append(dict(name=m[1],qty=int(m[2]),amount=num(seg[i+1].strip()[:-1])))
   gross=re.search(r'\n주문금액\s*([\d,]+)\s*원',c)
   if gross and found and sum(x['amount'] for x in found)==num(gross.group(1)):items=found;basis='배민 펼친 상품 상세와 주문금액 일치'
  orders.append(dict(date=dt,channel='baemin',store=store,sales=payment,items=items,basis=basis))
 cancel=json.loads((PRIVATE/f'baemin-{ "coffee" if store=="커피" else "gelato"}-jul-aug-cancelled.json').read_text())
 cancelMonthly=Counter('-'.join(re.search(r'주문시각\s*(\d{4})\.\s*(\d{2})\.\s*(\d{2})',c).groups())[:7] for c in cancel['cards'])
 for m in ['2026-07','2026-08']:
  rs=[o for o in orders if o['channel']=='baemin' and o['store']==store and o['date'].startswith(m)]
  meta.append(dict(month=m,channel='baemin',store=store,completedOrders=len(rs),cancelledOrders=cancelMonthly[m],sales=sum(r['sales'] for r in rs),basis='배달완료 주문 결제금액 · 취소 별도 제외',status='확보'))
for store,m,file in [('커피','2026-07','coupang_eats_2026-07 (1).xlsx'),('커피','2026-08','coupang_eats_2026-08 (2).xlsx'),('젤라또','2026-08','coupang_eats_2026-08 (3).xlsx')]:
 groups=defaultdict(list);financial=defaultdict(int)
 for r in load_workbook(DL/file,read_only=True,data_only=True).active.values:
  if not(r[0] and str(r[0]).startswith(m) and r[2]):continue
  assert r[6]==('이코복스커피 스튜디오 이태원점' if store=='커피' else '로렌조 젤라또')
  groups[str(r[2])].append(r)
  for i,k in [(9,'gross'),(10,'sales'),(11,'customerPayment'),(12,'platformCoupon'),(13,'merchantCoupon')]:financial[k]+=num(r[i])
 for oid,rs in groups.items():
  sales=sum(num(r[10]) for r in rs);dt=str(next((r[0] for r in rs if r[8]=='결제'),rs[0][0]));items=otter_items(oid) if sales>0 else None
  if sales==0:continue
  orders.append(dict(date=dt,channel='coupang',store=store,sales=sales,items=items,basis='직접 주문번호와 오터 상품 연결' if items else None))
 meta.append(dict(month=m,channel='coupang',store=store,completedOrders=sum(sum(num(r[10]) for r in rs)>0 for rs in groups.values()),cancelledOrders=sum(sum(num(r[10]) for r in rs)==0 for rs in groups.values()),sales=financial['sales'],gross=financial['gross'],customerPayment=financial['customerPayment'],basis='판매금액인 주문금액 · 결제/취소 원본 부호 합산',status='확보'))
meta.append(dict(month='2026-07',channel='coupang',store='젤라또',completedOrders=0,cancelledOrders=None,sales=0,basis='7/1~7/31 매출 관리 화면에서 0원·0건 확인',status='화면 확인'))
# Per-order direct net is authoritative. Product weights only allocate its net; no repeated order/option quantities.
products=[];daily=defaultdict(lambda:dict(baemin=0,coupang=0))
for o in orders:
 daily[o['date']][o['channel']]+=o['sales'];items=o['items']
 if not items or not sum(i['amount'] for i in items)>0:
  products.append(dict(date=o['date'],channel=o['channel'],store=o['store'],name=f'[{"배민" if o["channel"]=="baemin" else "쿠팡이츠"} {o["store"]}] 상품 상세 미확인',category='상품 미확인',sales=o['sales'],qty=0,unknownQty=True,unallocated=True,gross=None,discount=None,source='direct-platform-20261028'));continue
 shares=allocate(o['sales'],[i['amount'] for i in items])
 for item,amount in zip(items,shares):products.append(dict(date=o['date'],channel=o['channel'],store=o['store'],name=item['name'],category='채널 미분류',sales=amount,qty=item['qty'] or 0,unknownQty=item['qty'] is None,unallocated=False,gross=None,discount=None,source='direct-platform-20261028',allocation='주문 순매출을 확인한 상품·옵션 금액 비율로 배분'))
merged={}
for r in products:
 k=(r['date'],r['channel'],r['store'],r['name'])
 if k not in merged:merged[k]={**r,'sales':0,'gross':None,'qty':0}
 x=merged[k];x['sales']+=r['sales'];x['qty']+=r['qty'];x['unknownQty']|=r['unknownQty']
products=list(merged.values())
assert sum(r['sales'] for r in products if r['channel']=='baemin')==7801100
for m in ['2026-07','2026-08']:
 for ch in ['baemin','coupang']:assert sum(r['sales'] for r in products if r['date'].startswith(m) and r['channel']==ch)==sum(r['sales'] for r in meta if r['month']==m and r['channel']==ch)
# Direct delivery overrides the POS delivery-app category and all Otter transition totals.
a=json.loads((ROOT/'dist/analysis-data.json').read_text());nav=json.loads((ROOT/'dist/channel-data.json').read_text())
ledgerPath=ROOT/'dist/data.json';ledger=json.loads(ledgerPath.read_text());backup=ROOT/'reconciliations/prior-delivery-ledger-jul-aug.json'
if not backup.exists():backup.write_text(json.dumps([r for r in ledger['daily'] if '2026-07-01'<=r['date']<='2026-08-31'],ensure_ascii=False,indent=2))
old={r['date']:r for r in json.loads(backup.read_text())};pos=defaultdict(int);posDelivery=defaultdict(int);ns=defaultdict(int)
for r in a['products']:
 if '2026-07-01'<=r['date']<='2026-08-31':
  if r['category']=='배달앱':posDelivery[r['date']]+=num(r['sales'])
  else:pos[r['date']]+=num(r['sales'])
for r in nav['products']:
 if r['channel']=='naver':ns[r['date']]+=r['sales']
changes=[]
for row in ledger['daily']:
 d=row['date']
 if not '2026-07-01'<=d<='2026-08-31':continue
 total=pos[d]+daily[d]['baemin']+daily[d]['coupang']+ns[d]
 changes.append(dict(date=d,prior=old[d]['sales'],sales=total,payhereStore=pos[d],excludedPosDelivery=posDelivery[d],baemin=daily[d]['baemin'],coupang=daily[d]['coupang'],naver=ns[d]))
 row.update(sales=total,orders=None,revenueBasis='POS 상품(배달앱 제외) + 배민 커피·젤라또 + 쿠팡이츠 커피·젤라또 + 네이버',reconciliation='direct-platform-replaced',note=old[d].get('note',''))
ledger['updated']='2026-10-28';ledgerPath.write_text(json.dumps(ledger,ensure_ascii=False,separators=(',',':')))
output=dict(revision='2026-10-28-direct-platform',start='2026-07-01',end='2026-08-31',stores=meta,products=products,daily=changes,policy='7~8월은 POS 배달앱과 오터를 제외하고 배민·쿠팡이츠 직접 원본으로 대체. 네이버는 기존 확인 원본 합산. 주문 수는 POS 원본에 없어 전체 거래건수 미표시. 원본 할인·취소를 재차 차감하지 않음. 상품 미확인 금액 보존. 배분 상품액은 순매출이며 할인 전 총매출·상품별 할인액을 추정하지 않음.',definitions=[dict(label='쿠팡이츠 판매금액 기준',url='https://partners.coupangeats.com/start-guide/step-4/3385/'),dict(label='배민 주문내역',url='https://self.baemin.com/orders/history')])
(ROOT/'dist/direct-delivery.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')))
(ROOT/'reconciliations/direct-delivery-review.json').write_text(json.dumps({k:v for k,v in output.items() if k!='products'},ensure_ascii=False,indent=2))
print(json.dumps(dict(stores=meta,months=[dict(month=m,old=sum(r['prior'] for r in changes if r['date'].startswith(m)),sales=sum(r['sales'] for r in changes if r['date'].startswith(m))) for m in ['2026-07','2026-08']],productRows=len(products),unallocated=sum(r['sales'] for r in products if r['unallocated'])),ensure_ascii=False))
