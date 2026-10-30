"""Fetch public weather only; preserve KMA dash/blank values and raw manual store weather separately."""
from pathlib import Path
import urllib.request,urllib.parse,json,re,html,concurrent.futures,datetime,hashlib,csv
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
ledger=json.loads((ROOT/'dist/data.json').read_text())
END=min(max(r['date'] for r in ledger['daily']),(datetime.datetime.now(ZoneInfo('Asia/Seoul')).date()-datetime.timedelta(days=1)).isoformat())
BASE='https://www.weather.go.kr/w/weather/land/past-obs/obs-by-day.do'
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'IKOVOX-store-weather-review/1.0'})
 with urllib.request.urlopen(req,timeout=30) as r:return r.read().decode('utf-8')
def parse(text,year,month,obs):
 block=re.search(r'<table[^>]*class="[^"]*table-cal[^"]*"[^>]*>(.*?)</table>',text,re.S)
 if not block:raise ValueError('KMA weather calendar absent')
 dates=[];out={}
 for tr in re.findall(r'<tr[^>]*>(.*?)</tr>',block[1],re.S):
  tds=[html.unescape(re.sub('<[^>]+>',' ',td)) for td in re.findall(r'<td[^>]*>(.*?)</td>',tr,re.S)]
  tds=[' '.join(t.split()) for t in tds]
  if any(re.fullmatch(r'\d+일',s) for s in tds):dates=[int(s[:-1]) if re.fullmatch(r'\d+일',s) else None for s in tds];continue
  if not dates or not tds:continue
  for day,value in zip(dates,tds):
   if day is None:continue
   date=f'{year}-{month:02}-{day:02}'
   if date>END:continue
   if obs==1:
    def metric(label):
     m=re.search(label+r':\s*(-?\d+(?:\.\d+)?)',value);return float(m[1]) if m else None
    vals={k:metric(v) for k,v in [('tempMean','평균기온'),('tempMax','최고기온'),('tempMin','최저기온'),('cloud','평균운량'),('precipitation','일강수량')]}
    raw=re.search(r'일강수량:\s*(.*?)(?:\s|$)',value);vals['precipitationRaw']=raw[1] if raw else ''
    if vals['tempMean'] is not None:out[date]=dict(date=date,**vals)
   else:out[date]=value
 return out
last=datetime.date.fromisoformat(END)
jobs=[(y,m,o) for y in range(2025,last.year+1) for m in range(1,(last.month if y==last.year else 12)+1) for o in [1,9]]
def month_job(job):
 y,m,o=job;url=BASE+'?'+urllib.parse.urlencode(dict(stn=108,yy=y,mm=m,obs=o));text=fetch(url);heading=re.search(r'cmp-table-topinfo.*?</p>',text,re.S);assert heading and f'{y}년 {m}월' in heading[0],'KMA period mismatch';return job,parse(text,y,m,o),hashlib.sha256(text.encode()).hexdigest()
rows={};phenomena={};sources=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for (y,m,o),data,sha in pool.map(month_job,jobs):
  (rows if o==1 else phenomena).update(data);sources.append(dict(year=y,month=m,element=o,sha256=sha,records=len(data)))
url='https://archive-api.open-meteo.com/v1/archive?'+urllib.parse.urlencode(dict(latitude=37.5345,longitude=126.9946,start_date='2025-01-01',end_date=END,daily='wind_speed_10m_max,wind_gusts_10m_max',timezone='Asia/Seoul',wind_speed_unit='ms'))
wind=json.loads(fetch(url));assert wind['daily_units']['wind_speed_10m_max']=='m/s'
wmap={d:{'windMax':wind['daily']['wind_speed_10m_max'][i],'gustMax':wind['daily']['wind_gusts_10m_max'][i]} for i,d in enumerate(wind['daily']['time'])}
for d,r in rows.items():
 r['phenomena']=phenomena.get(d,'').replace('\xa0',' ').strip();r.update(wmap.get(d,dict(windMax=None,gustMax=None)))
 if '눈' in r['phenomena']:r['condition']='눈'
 elif '비' in r['phenomena'] or (r['precipitation'] is not None and r['precipitation']>0):r['condition']='비'
 elif r['cloud'] is None:r['condition']='현상 미확인'
 elif r['cloud']<=2:r['condition']='맑음'
 elif r['cloud']<=5:r['condition']='구름 조금'
 elif r['cloud']<=8:r['condition']='구름 많음'
 else:r['condition']='흐림'
expected=(datetime.date.fromisoformat(END)-datetime.date(2025,1,1)).days+1

if len(rows)!=expected:print('month coverage',[(s['year'],s['month'],s['records']) for s in sources if s['element']==1])
assert len(rows)==expected,(len(rows),expected)
assert all(r['tempMin']<=r['tempMean']<=r['tempMax'] for r in rows.values())
out=dict(asOf=END,timezone='Asia/Seoul',period='00:00~24:00',station=dict(id='108',name='서울(유)',provider='기상청 날씨누리',url=BASE+'?stn=108'),windSource=dict(provider='Open-Meteo Historical Weather',kind='인근 격자 재분석 추정',requestedLatitude=37.5345,requestedLongitude=126.9946,gridLatitude=wind['latitude'],gridLongitude=wind['longitude'],url='https://open-meteo.com/en/docs/historical-weather-api'),note='기온·강수·현상은 서울 관측소(108), 바람은 이태원 인근 격자 재분석자료. 루프탑 실측과 다를 수 있음. 기상청 강수 -/공백은 숫자 0으로 바꾸지 않음. 서울 일자 00~24시 기준. 기존 매장 날씨 메모는 별도 보존.',daily=sorted(rows.values(),key=lambda r:r['date']))
(ROOT/'dist/weather-data.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
(ROOT/'reconciliations/weather-import.json').write_text(json.dumps(dict(asOf=END,records=len(rows),sources=sources,notes=out['note']),ensure_ascii=False,indent=2))
print(json.dumps(dict(days=len(rows),last=out['daily'][-1],windDays=sum(r['windMax'] is not None for r in rows.values()),rainDashDays=sum(r['precipitationRaw']=='-' for r in rows.values())),ensure_ascii=False))

with (ROOT/'dist/weather-data.csv').open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.writer(f);fields=['date','condition','tempMean','tempMin','tempMax','precipitation','precipitationRaw','windMax','gustMax','phenomena'];writer.writerow(fields);writer.writerows([[r.get(k,'') for k in fields] for r in out['daily']])
