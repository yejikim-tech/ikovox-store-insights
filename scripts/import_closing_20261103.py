"""Import November 3 closing data read from authenticated, visible administrator UI."""
from pathlib import Path
from collections import defaultdict
import json,re,hashlib,csv
R=Path(__file__).resolve().parents[1];P=R.parent/'audit/private';DAYS=['2026-11-03']
read=lambda f:json.loads((R/'dist'/f).read_text())
def save(f,x):(R/'dist'/f).write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
def num(x):return int(re.sub('[^0-9-]','',str(x)) or 0)
def date(s):
 m=re.search(r'(2026)\.\s*(\d+)\.\s*(\d+)' ,s);assert m,s;return f'{m[1]}-{int(m[2]):02}-{int(m[3]):02}'
def parse_nodes(nodes):
 parents=[];i=0
 while i<len(nodes):
  n=nodes[i]
  if n['tag']=='SPAN' and n['text'].isdigit():
   assert nodes[i+1]['tag']=='SPAN' and nodes[i+2]['tag']=='DIV';parents.append(dict(qty=num(n['text']),name=nodes[i+1]['text'].strip(),unit=num(nodes[i+2]['text']),options=[]));i+=3
  elif n['role']=='group':
   cs=n['children'];assert len(cs)%3==0
   for j in range(0,len(cs),3):parents[-1]['options'].append(dict(qty=num(cs[j]['text']),name=cs[j+1]['text'].strip(),unit=num(cs[j+2]['text'])))
   i+=1
  else:assert n['text']=='';i+=1
 return parents
raw=json.loads((P/'payhere-20261103-products-ui.json').read_text());assert '26.11.03 ~ 26.11.03' in raw['body'] and '총 52개' in raw['body'] and len(raw['rows'])==52
sid='payhere-ui-'+hashlib.sha256((P/'payhere-20261103-products-ui.json').read_bytes()).hexdigest()[:16]
pos=[];totals=defaultdict(lambda:defaultdict(int))
for r in raw['rows']:
 d=date(r[2]);assert d in DAYS and len(r)==15
 x=dict(date=d,category=r[0],name=r[1],unitPrice=num(r[3]),qty=num(r[6]),sold=None,gross=num(r[8]),sales=num(r[9]),discount=num(r[10]),points=num(r[11]),prepaid=num(r[12]),refund=num(r[13]),refundQty=num(r[14]),source=sid)
 pos.append(x)
 for k in ['qty','gross','sales','discount','points','prepaid','refund','refundQty']:totals[d][k]+=x[k]
assert [totals[d]['sales'] for d in DAYS]==[1692000]
assert sum(totals[d]['sales'] for d in DAYS)==1692000 and sum(totals[d]['refund'] for d in DAYS)==0
assert not any(r['category']=='배달앱' for r in pos)
orders=json.loads((P/'otter-20261103-ui.json').read_text())['rows'];assert len(orders)==len(set(r[1] for r in orders))==16
lookup={r['key']:r for r in json.loads((P/'otter-20261103-structured.json').read_text())};assert len(lookup)==16
products=[];daily=defaultdict(lambda:dict(otter=0,otterOrders=0,otterCancelled=0,otterUnallocated=0,naver=0,naverOrders=0,naverCancelled=0));issues=[]
for r in orders:
 d=date(r[0]);assert d in DAYS
 if r[5]=='취소됨':daily[d]['otterCancelled']+=1;continue
 assert r[5]=='완료된 주문' and r[7]=='Paid'
 gross=num(r[11]);discount=-num(r[15]);net=gross-discount;daily[d]['otter']+=net;daily[d]['otterOrders']+=1
 detail=lookup[r[1]];assert '#'+r[1] in detail['text'];parents=parse_nodes(detail['nodes']);weights=[v['qty']*(v['unit']+sum(o['qty']*o['unit'] for o in v['options'])) for v in parents]
 if sum(weights)!=gross or sum(v['qty'] for v in parents)!=num(r[10]):
  issues.append(dict(date=d,gross=gross,receiptGross=sum(weights),menuCount=num(r[10]),receiptCount=sum(v['qty'] for v in parents),names=[p['name'] for p in parents]));daily[d]['otterUnallocated']+=net
  products.append(dict(date=d,channel='otter',category='상품 미확인',name='[오터] 상품 상세 미확인',sales=net,qty=0,unallocated=True,unknownQty=True,source='otter-20261103-ui'));continue
 alloc=[discount*w//gross for w in weights]
 for j in sorted(range(len(weights)),key=lambda j:-(discount*weights[j]%gross))[:discount-sum(alloc)]:alloc[j]+=1
 for v,w,disc in zip(parents,weights,alloc):products.append(dict(date=d,channel='otter',category='채널 미분류',name=v['name'],qty=v['qty'],gross=w,discount=disc,sales=w-disc,refund=0,refundQty=0,points=0,prepaid=0,source='otter-20261103-ui'))
assert [daily[d]['otter'] for d in DAYS]==[312700]
navList=json.loads((P/'naver-20261103-list.json').read_text());assert '26. 11. 3.화' in navList['body']
nav=json.loads((P/'naver-20261103-details.json').read_text());assert len(nav)==len(set(x['href'] for x in navList['links']))==1
for r in nav:
 t=r['text'];assert r['href'].split('/')[-1] in t;assert '결제완료' in t and '픽업완료' in t
 m=re.search(r'26\.(\d+)\.(\d+)\.[^\n]*\(주문접수\)',t);assert m;d=f'2026-{int(m[1]):02}-{int(m[2]):02}';assert d in DAYS
 area=t[t.index('원결제금액'):t.index('직원메모')];lines=[s.strip() for s in area.splitlines() if s.strip()];amount=num(lines[0].split('원결제금액')[1]);items=[];current=None
 for line in lines[1:]:
  if re.fullmatch(r'[\d,]+원',line):
   assert current;current['sales']=num(line);items.append(current);current=None
  elif current is None:
   m=re.fullmatch(r'(.+)\((\d+)\)',line);assert m,line;current=dict(name=m[1],qty=int(m[2]))
 assert sum(x['sales'] for x in items)==amount
 assert not re.search(r'(환불금액|환불완료|결제취소)',t)
 daily[d]['naver']+=amount;daily[d]['naverOrders']+=1
 for x in items:products.append(dict(date=d,channel='naver',category='채널 미분류',gross=x['sales'],discount=0,refund=0,refundQty=0,points=0,prepaid=0,source='naver-20261103-ui',**x))
assert [daily[d]['naver'] for d in DAYS]==[25200]
a=read('analysis-data.json');a['products']=[r for r in a['products'] if r['date'] not in DAYS]+pos;a['productCoverage']=sorted(set(a['productCoverage']+DAYS));a['partialProductDates']=[d for d in a['partialProductDates'] if d not in DAYS]
a['dailyProductTotals']=[r for r in a['dailyProductTotals'] if r['date'] not in DAYS]+[dict(date=d,partial=False,source=sid,**totals[d]) for d in DAYS];a['dailyProductTotals'].sort(key=lambda r:r['date']);a['importSources']=[r for r in a['importSources'] if r['id']!=sid]+[dict(id=sid,label='페이히어 2026-11-03 상품별·일자별 관리자 원본',kind='products',start=DAYS[0],end=DAYS[-1],records=len(pos),days=1,note='관리자 전체 52행·실매출 1,692,000원 대조.')];a['importRevision']='2026-11-04-closing'
ch=read('channel-data.json');ch['products']=[r for r in ch['products'] if r['date'] not in DAYS]+products;ch['daily']=[r for r in ch['daily'] if r['date'] not in DAYS]+[dict(date=d,**daily[d]) for d in DAYS];ch['daily'].sort(key=lambda r:r['date']);ch['asOf']=DAYS[-1];ch['revision']='2026-11-04-closing'
for c in ch['coverage']:
 if c['channel'] in ['payhere','otter','naver']:c['end']=DAYS[-1]
b=read('data.json');historical=[r for r in b['daily'] if r['date'] not in DAYS];b['daily']=historical+[dict(date=d,sales=totals[d]['sales']+daily[d]['otter']+daily[d]['naver'],orders=None,weather='',promotion='',note='11/4 관리자 마감 원본 대조. POS 상품 실매출 및 배달 완료 주문 소계에서 가맹점 할인 반영. 네이버 완료 1건·25,200원 접수일 기준. POS 환불은 원본 별도 표시.',revenueBasis='POS 실매출 + 오터 완료 순매출 + 네이버 완료 주문 접수일',reconciliation='daily-originals-verified') for d in DAYS];b['daily'].sort(key=lambda r:r['date']);b['updated']='2026-11-04'
assert [r['sales'] for r in b['daily'] if r['date'] in DAYS]==[2029900]
assert sum(r['sales'] for r in historical)==874930780
originalPos=defaultdict(int)
for r in a['products']:originalPos[r['date']]+=r['sales']
for month in sorted(set(d[:7] for d in DAYS)):
 ds=[r['date'] for r in b['daily'] if r['date'].startswith(month)];source=[r for r in ch['daily'] if r['date'].startswith(month)];previous=next((r for r in ch['months'] if r['month']==month),{})
 entry={**previous,'month':month,'payhere':sum(originalPos[d] for d in ds),'posDays':len(ds),'excludedPosDelivery':0,'appliedDelivery':sum(r['otter'] for r in source),'otter':sum(r['otter'] for r in source),'otterOrders':sum(r['otterOrders'] for r in source),'otterUnallocated':sum(r.get('otterUnallocated',0) for r in source),'naver':sum(r['naver'] for r in source),'naverOrders':sum(r['naverOrders'] for r in source),'reconciledTotal':sum(r['sales'] for r in b['daily'] if r['date'].startswith(month)),'legacyDays':len(ds),'status':'POS + 오터 + 네이버 원본 순매출'}
 assert entry['payhere']+entry['appliedDelivery']+entry['naver']==entry['reconciledTotal']
 ch['months']=[r for r in ch['months'] if r['month']!=month]+[entry]
ch['months'].sort(key=lambda r:r['month'])
for f,x in [('analysis-data.json',a),('channel-data.json',ch),('data.json',b)]:save(f,x)
with (R/'dist/channel-monthly-audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['월','POS 원본','제외 POS 배달앱','적용 배달 순매출','네이버 완료액','통합 총매출','기준']);w.writerows([[r[k] for k in ['month','payhere','excludedPosDelivery','appliedDelivery','naver','reconciledTotal','status']] for r in ch['months']])
report=dict(start=DAYS[0],end=DAYS[-1],days=[dict(date=d,pos=totals[d]['sales'],**daily[d],total=totals[d]['sales']+daily[d]['otter']+daily[d]['naver']) for d in DAYS],annual=sum(r['sales'] for r in b['daily']),posProducts=len(pos),deliveryProductIssues=issues,policy='완료 주문·가맹점 할인 반영. 전체 취소 제외. 네이버 접수일 기준. 원본 환불은 별도 보존.')
(R/'reconciliations/20261103-closing.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
