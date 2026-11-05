"""Import exact weekly POS option exports without prorating the older period totals."""
from pathlib import Path
import hashlib,json,re,unicodedata,warnings
from openpyxl import load_workbook
warnings.filterwarnings('ignore',category=UserWarning)
root=Path(__file__).resolve().parents[1]
path=root/'public/analysis-data.json';a=json.loads(path.read_text());summaries=[]
for p in sorted((Path.home()/'Downloads').glob('*.xlsx')):
 name=unicodedata.normalize('NFC',p.name)
 if '옵션별 조회(옵션별)' not in name:continue
 match=re.search(r'_(2026-\d\d-\d\d)~(2026-\d\d-\d\d)\.xlsx$',name)
 if not match:continue
 start,end=match.groups()
 from datetime import date
 if (date.fromisoformat(end)-date.fromisoformat(start)).days!=6 or date.fromisoformat(start).weekday()!=0:continue
 rows=list(load_workbook(p,read_only=True,data_only=True).active.values)
 assert rows[3][0]==f'기간:{start}~{end}'
 assert rows[6][:7]==('매장명','옵션명','카테고리명','상품명','판매가','총 주문 건수','옵션 선택 건수')
 digest=hashlib.sha256(p.read_bytes()).hexdigest();source='xlsx-'+digest[:16];records=[]
 for i,r in enumerate(rows[7:],8):
  if not any(v is not None for v in r):continue
  assert r[0]=='이코복스 이태원점' and r[1] and r[3] and r[6]>=0
  records.append(dict(store=r[0],option=r[1],category=r[2],name=r[3],unitPrice=r[4],orderCount=r[5],selections=r[6],sales=r[7],averagePrice=r[8],selectionRate=r[9],start=start,end=end,source=source,sourceRow=i))
 replaced={s['id'] for s in a['importSources'] if s['kind']=='options' and s['start']==start and s['end']==end}
 a['options']=[r for r in a['options'] if r['source'] not in replaced]+records
 a['importSources']=[s for s in a['importSources'] if s['id'] not in replaced]
 info=dict(id=source,label=name,start=start,end=end,kind='options',sha256=digest,records=len(records),selections=sum(r['selections'] for r in records),optionSales=sum(r['sales'] for r in records),complete=True,scope='weekly')
 a['importSources'].append(info);summaries.append(info)
assert summaries,'No exact Monday–Sunday option export found'
path.write_text(json.dumps(a,ensure_ascii=False,separators=(',',':')))
(root/'reconciliations/weekly-options.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2))
print(json.dumps([dict(start=s['start'],end=s['end'],records=s['records'],selections=s['selections']) for s in summaries],ensure_ascii=False))
