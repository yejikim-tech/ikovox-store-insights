"""Import captured, complete Payhere weekly options tables without prorating."""
from pathlib import Path
import json,hashlib,re
root=Path(__file__).resolve().parents[1]
private=root.parent/'audit/private'
pages=[json.loads((private/f'payhere-week20261026-options-page{i}.json').read_text()) for i in (1,2)]
rows=pages[0]['rows']+pages[1]['rows'];assert len(rows)==317
assert all(len(r)==11 for r in rows)
def num(x):return int(re.sub(r'[^0-9-]','',str(x)) or '0')
digest=hashlib.sha256(json.dumps(rows,ensure_ascii=False).encode()).hexdigest();source='payhere-options-ui-'+digest[:16]
records=[dict(store='이코복스 이태원점',category=r[0],name=r[1],unitPrice=num(r[2]),orderCount=num(r[4]),optionGroup=r[5],option=r[6],selections=num(r[7]),sales=num(r[8]),averagePrice=num(r[9]),selectionRate=r[10],start='2026-10-26',end='2026-11-01',source=source,sourceRow=i+1) for i,r in enumerate(rows)]
p=root/'public/analysis-data.json';a=json.loads(p.read_text());old={s['id'] for s in a['importSources'] if s['kind']=='options' and s['start']=='2026-10-26' and s['end']=='2026-11-01'}
a['options']=[r for r in a['options'] if r['source'] not in old]+records
info=dict(id=source,label='페이히어 2026-10-26~2026-11-01 옵션별 관리자 원본',start='2026-10-26',end='2026-11-01',kind='options',sha256=digest,records=317,selections=sum(r['selections'] for r in records),optionSales=sum(r['sales'] for r in records),complete=True,scope='weekly')
a['importSources']=[s for s in a['importSources'] if s['id'] not in old]+[info];p.write_text(json.dumps(a,ensure_ascii=False,separators=(',',':')))
p=root/'reconciliations/weekly-options.json';prior=json.loads(p.read_text());prior=[s for s in prior if s['start']!='2026-10-26'];p.write_text(json.dumps(prior+[info],ensure_ascii=False,indent=2));print(info)
