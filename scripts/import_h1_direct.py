"""Reconcile the H1 direct originals; publish no order identifiers or customer data."""
from pathlib import Path
from collections import defaultdict,Counter
from datetime import date,timedelta
import json,re,warnings
from openpyxl import load_workbook
warnings.filterwarnings('ignore',category=UserWarning)
ROOT=Path(__file__).resolve().parents[1];PRIVATE=ROOT.parent/'audit/private';DL=Path.home()/'Downloads'
read=lambda p:json.loads(p.read_text())
write=lambda p,x:p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
num=lambda v:round(float(str(v or 0).replace(',','')))
cards=[c for p in read(PRIVATE/'baemin-coffee-h1-pages.json') for c in p['cards']]
corrections=read(PRIVATE/'baemin-h1-order-corrections.json');correction={r['orderKey']:r for r in corrections}
assert len(correction)==len(corrections)
assert sum(r['discountMissing'] for r in corrections)==6000,'Every discount difference needs an identified original order'
refunds=read(PRIVATE/'baemin-h1-partial-refunds.json');assert len(refunds)==3
assert sum(r['refund'] for r in refunds)==30400
refundByDate={r['date']:r['refund'] for r in refunds}
orders=[];seen=set();daily=defaultdict(lambda:dict(baemin=0,coupang=0));products=[]
for c in cards:
 oid=re.search(r'배달완료\s*([A-Z0-9]+)',c).group(1);assert oid not in seen;seen.add(oid)
 dt='-'.join(re.search(r'주문시각\s*(\d{4})\.\s*(\d\d)\.\s*(\d\d)',c).groups())
 amount=num(re.search(r'결제금액\s*(?:부분취소\s*)?([\d,]+)원',c).group(1))
 if oid in correction:assert correction[oid]['header']==amount;amount=correction[oid]['sales']
 partial=bool(re.search(r'결제금액\s*부분취소',c.split('접기')[0]))
 if partial:assert dt in refundByDate;amount-=refundByDate[dt]
 orders.append(dict(date=dt,sales=amount));daily[dt]['baemin']+=amount
 # Allocate only when expanded item totals reconcile to the source's food amount.
 detail=correction.get(oid,{}).get('proof',c);items=[]
 if not partial and '주문 추가 정보 보기' in detail:
  lines=detail.split('주문 추가 정보 보기',1)[1].split('총 결제금액')[0].splitlines()
  for j,line in enumerate(lines[:-1]):
   m=re.fullmatch(r'(.*?)(\d+)개',line.strip())
   if m and re.fullmatch(r'[\d,]+원',lines[j+1].strip()):items.append(dict(name=m[1],qty=int(m[2]),amount=num(lines[j+1].strip()[:-1])))
  g=re.search(r'\n주문금액\s*([\d,]+)\s*원',detail)
  if not g or sum(i['amount'] for i in items)!=num(g.group(1)):items=[]
 if items:
  denominator=sum(i['amount'] for i in items);shares=[amount*i['amount']//denominator for i in items]
  for j in sorted(range(len(items)),key=lambda j:-(amount*items[j]['amount']%denominator))[:amount-sum(shares)]:shares[j]+=1
  for item,share in zip(items,shares):products.append(dict(date=dt,channel='baemin',store='커피',name=item['name'],category='채널 미분류',sales=share,qty=item['qty'],unknownQty=False,unallocated=False,gross=None,discount=None,source='direct-h1-20261029',allocation='확인된 상품·옵션 금액 비율로 주문 순매출 배분'))
 else:products.append(dict(date=dt,channel='baemin',store='커피',name='[배민 커피] 상품 상세 미확인',category='상품 미확인',sales=amount,qty=0,unknownQty=True,unallocated=True,gross=None,discount=None,source='direct-h1-20261029'))
assert len(seen)==583
assert sum(r['sales'] for r in orders)==12301400-30400
cpMonth=defaultdict(int);cpGroups=defaultdict(list)
for file in ['coupang_eats_2026-Q1.xlsx','coupang_eats_2026-04.xlsx','coupang_eats_2026-05.xlsx','coupang_eats_2026-06.xlsx']:
 for r in load_workbook(DL/file,read_only=True,data_only=True).active.values:
  if not(r[0] and re.fullmatch(r'2026-\d\d-\d\d',str(r[0])) and r[2]):continue
  dt=str(r[0]);assert '2026-01-01'<=dt<='2026-06-30';assert r[6]=='이코복스커피 스튜디오 이태원점'
  amount=num(r[10]);cpGroups[(dt[:7],str(r[2]))].append(r)
  cpMonth[dt[:7]]+=amount;daily[dt]['coupang']+=amount
  products.append(dict(date=dt,channel='coupang',store='커피',name='[쿠팡이츠 커피] 상품 상세 미확인',category='상품 미확인',sales=amount,qty=0,unknownQty=True,unallocated=True,gross=None,discount=None,source='direct-h1-20261029'))
assert dict(cpMonth)==dict(zip([f'2026-{m:02}' for m in range(1,7)],[7944200,7057600,6496600,6992400,6773900,8601500]))
merged={}
for r in products:
 key=(r['date'],r['channel'],r['name'])
 if key not in merged:merged[key]={**r,'sales':0,'qty':0}
 merged[key]['sales']+=r['sales'];merged[key]['qty']+=r['qty']
products=list(merged.values())
a=read(ROOT/'public/analysis-data.json');ch=read(ROOT/'public/channel-data.json');direct=read(ROOT/'public/direct-delivery.json');ledger=read(ROOT/'public/data.json')
pos=defaultdict(int);excluded=defaultdict(int);nav=defaultdict(int)
for r in a['products']:
 if '2026-01-01'<=r['date']<='2026-06-30':(excluded if r['category']=='배달앱' else pos)[r['date']]+=num(r['sales'])
for r in ch['products']:
 if r['channel']=='naver':nav[r['date']]+=r['sales']
changes=[];newLedger=[]
for i in range(181):
 dt=(date(2026,1,1)+timedelta(days=i)).isoformat();assert dt in a['productCoverage']
 total=pos[dt]+daily[dt]['baemin']+daily[dt]['coupang']+nav[dt]
 changes.append(dict(date=dt,prior=None,sales=total,payhereStore=pos[dt],excludedPosDelivery=excluded[dt],baemin=daily[dt]['baemin'],coupang=daily[dt]['coupang'],naver=nav[dt]))
 newLedger.append(dict(date=dt,sales=total,orders=None,weather='',promotion='',note='',revenueBasis='POS 상품(배달앱 제외) + 배민·쿠팡이츠 직접 순매출 + 네이버 완료액',reconciliation='direct-platform-replaced'))
cancel=read(PRIVATE/'baemin-coffee-h1-cancelled.json');cancelMonths=Counter('-'.join(re.search(r'주문시각\s*(\d{4})\.\s*(\d\d)\.\s*(\d\d)',c).groups())[:7] for c in cancel['cards'])
meta=[]
for month in [f'2026-{m:02}' for m in range(1,7)]:
 for platform in ['baemin','coupang']:
  rs=[o for o in orders if o['date'].startswith(month)]
  groups=[rs for (m,k),rs in cpGroups.items() if m==month]
  meta.append(dict(month=month,channel=platform,store='커피',completedOrders=len(rs) if platform=='baemin' else sum(sum(num(r[10]) for r in rows)>0 for rows in groups),cancelledOrders=cancelMonths[month] if platform=='baemin' else sum(sum(num(r[10]) for r in rows)==0 for rows in groups),sales=sum(x[platform] for d,x in daily.items() if d.startswith(month)),basis='주문금액에서 확인한 가맹점 할인·부분환불 반영, 전체 취소 제외' if platform=='baemin' else '주문금액 열의 결제·취소 이벤트를 발생일별 부호 합산',status='확보'))
  meta.append(dict(month=month,channel=platform,store='젤라또',completedOrders=0,cancelledOrders=0,sales=0,basis='1/1~6/30 전체 조회 0건·0원 확인',status='화면 확인'))
direct['products']=[r for r in direct['products'] if r['date']>'2026-06-30']+products
direct['daily']=sorted([r for r in direct['daily'] if r['date']>'2026-06-30']+changes,key=lambda r:r['date'])
direct['stores']=[r for r in direct['stores'] if r['month']>'2026-06']+meta
direct.update(start='2026-01-01',revision='2026-10-29-h1-reconciled',policy='1~8월은 POS 배달앱과 오터를 제외하고 배민·쿠팡이츠 직접 원본으로 대체합니다. 배민은 가맹점 할인 및 확인된 부분환불을 반영하고 전체 취소를 제외합니다. 쿠팡이츠는 판매금액인 주문금액의 결제·취소 부호를 발생일 기준으로 합산합니다. 네이버 완료액을 추가합니다. 상품 상세 미확인액은 별도 보존하며 옵션 금액을 중복 합산하지 않습니다.')
ledger['daily']=sorted([r for r in ledger['daily'] if r['date']>'2026-06-30']+newLedger,key=lambda r:r['date']);ledger['updated']='2026-10-29'
assert len(ledger['daily'])==301 and len({r['date'] for r in ledger['daily']})==301
write(ROOT/'public/direct-delivery.json',direct);write(ROOT/'public/data.json',ledger)
report=dict(start='2026-01-01',end='2026-06-30',days=181,baeminHeader=12307400,baeminMerchantDiscountCorrections=6000,baeminPartialRefunds=30400,baeminNet=12271000,coupangNet=sum(cpMonth.values()),months=[dict(month=m,sales=sum(r['sales'] for r in changes if r['date'].startswith(m)),pos=sum(r['payhereStore'] for r in changes if r['date'].startswith(m)),baemin=sum(r['baemin'] for r in changes if r['date'].startswith(m)),coupang=sum(r['coupang'] for r in changes if r['date'].startswith(m)),naver=sum(r['naver'] for r in changes if r['date'].startswith(m))) for m in cpMonth],privacy='주문번호·고객정보는 공개 집계에 포함하지 않음')
write(ROOT/'reconciliations/h1-direct-review.json',report);print(json.dumps(report,ensure_ascii=False))
