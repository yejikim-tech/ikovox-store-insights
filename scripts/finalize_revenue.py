"""Use one channel definition for every headline and export, preserving prior values."""
from pathlib import Path
from collections import defaultdict
import csv,json
ROOT=Path(__file__).resolve().parents[1]
read=lambda name:json.loads((ROOT/'dist'/name).read_text())
write=lambda name,x:(ROOT/'dist'/name).write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
ledger=read('data.json');analysis=read('analysis-data.json');channels=read('channel-data.json');direct=read('direct-delivery.json')
pos=defaultdict(int);excluded=defaultdict(int);sourceDaily={r['date']:r for r in channels['daily']};directDaily={r['date']:r for r in direct['daily']}
for r in analysis['products']:
 pos[r['date']]+=round(r['sales'])
 if r['category']=='배달앱':excluded[r['date']]+=round(r['sales'])
backup=ROOT/'reconciliations/prior-sep-oct-ledger.json'
if not backup.exists():backup.write_text(json.dumps([r for r in ledger['daily'] if r['date']>='2026-09-01'],ensure_ascii=False,indent=2))
old={r['date']:r for r in json.loads(backup.read_text())};changes=[];monthRows=[]
for r in ledger['daily']:
 d=r['date']
 if d in directDaily:assert r['sales']==directDaily[d]['sales'];continue
 assert '2026-09-01'<=d<='2026-10-28'
 x=sourceDaily.get(d,{})
 total=pos[d]+x.get('otter',0)+x.get('naver',0)
 changes.append(dict(date=d,prior=old[d]['sales'],sales=total,pos=pos[d],otter=x.get('otter',0),naver=x.get('naver',0)))
 r.update(sales=total,revenueBasis='POS 상품 실매출 + 오터 완료 주문 순매출 + 네이버 완료액',reconciliation='original-channel-net')
for month in [f'2026-{m:02}' for m in range(1,11)]:
 rows=[r for r in ledger['daily'] if r['date'].startswith(month)];ds=[r['date'] for r in rows];dr=[directDaily[d] for d in ds if d in directDaily];isDirect=bool(dr)
 p=sum(pos[d] for d in ds);ex=sum(excluded[d] for d in ds) if isDirect else 0
 delivery=sum(r['baemin']+r['coupang'] for r in dr) if isDirect else sum(sourceDaily.get(d,{}).get('otter',0) for d in ds)
 nav=sum(r['naver'] for r in dr) if isDirect else sum(sourceDaily.get(d,{}).get('naver',0) for d in ds)
 total=sum(r['sales'] for r in rows);assert p-ex+delivery+nav==total
 previous=next((r for r in channels['months'] if r['month']==month),{})
 monthRows.append({**previous,'month':month,'payhere':p,'posDays':len(ds),'excludedPosDelivery':ex,'appliedDelivery':delivery,'naver':nav,'reconciledTotal':total,'status':'배민·쿠팡이츠 직접 순매출 · 할인·부분환불 반영' if isDirect else 'POS + 오터 + 네이버 원본 순매출'})
channels['months']=monthRows;channels['revision']='2026-10-29-reconciled';channels['policy']='매장 총매출 = POS 매장 실매출 + 배달 순매출 + 네이버 완료액. 1~8월은 POS 배달앱·오터를 제외하고 배민·쿠팡이츠 직접 원본을 사용합니다. 9~10월은 오터 완료 주문 순매출을 사용합니다.'
for coverage in channels['coverage']:
 if coverage['channel']=='naver':coverage.update(start='2026-01-01',note='전체 주문 조회에서 1/1~3/19 완료 주문 없음 확인. 실제 첫 관측 3/20. 완료 주문 실결제액만 집계, 10/28 0건 확인.')
channels['coverage']=[r for r in channels['coverage'] if r['channel'] not in ['baemin','coupang']]+[dict(channel=c,start='2026-01-01',end='2026-08-31',note='커피·젤라또 직접 관리자 원본. 가맹점 할인 및 확인한 취소·부분환불 반영.') for c in ['baemin','coupang']]
direct['stores'].sort(key=lambda r:(r['month'],r['channel'],r['store']));direct['daily'].sort(key=lambda r:r['date']);direct['revision']='2026-10-29-net-reconciled'
ledger['updated']='2026-10-29';write('data.json',ledger);write('channel-data.json',channels);write('direct-delivery.json',direct)
def csvout(name,headers,rows):
 with (ROOT/'dist'/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(headers);w.writerows(rows)
csvout('channel-monthly-audit.csv',['월','POS 원본','제외 POS 배달앱','적용 배달 순매출','네이버 완료액','통합 총매출','기준'],[[r[k] for k in ['month','payhere','excludedPosDelivery','appliedDelivery','naver','reconciledTotal','status']] for r in monthRows])
csvout('direct-delivery-review.csv',['날짜','POS 매장','제외 POS 배달앱','배민','쿠팡이츠','네이버','통합 총매출'],[[r[k] for k in ['date','payhereStore','excludedPosDelivery','baemin','coupang','naver','sales']] for r in direct['daily']])
csvout('excluded-pos-delivery.csv',['날짜','제외한 POS 배달앱 금액'],[[d,excluded[d]] for d in sorted(directDaily)])
report=dict(days=len(ledger['daily']),start=ledger['daily'][0]['date'],end=ledger['daily'][-1]['date'],total=sum(r['sales'] for r in ledger['daily']),months=monthRows,sepOctChanges=changes,h1MerchantDiscountCorrections=6000,h1PartialRefunds=30400,julAugPartialRefunds=33800,policy=channels['policy'])
(ROOT/'reconciliations/full-revenue-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(dict(days=report['days'],total=report['total'],months=[dict(month=r['month'],total=r['reconciledTotal']) for r in monthRows]),ensure_ascii=False))
