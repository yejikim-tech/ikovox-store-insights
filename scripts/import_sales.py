"""Read the seven supplied exports without editing them; reconcile before publishing."""
import collections, datetime, hashlib, json, pathlib, unicodedata
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parents[1]
periods = ['2025-01-01~2025-06-30', '2025-07-01~2025-11-30', '2025-12-01~2025-12-31',
           '2026-01-01~2026-06-30', '2026-07-01~2026-10-28']
analysis = json.loads((ROOT/'public/analysis-data.json').read_text())
products, options, totals, sources, adjustments = [], [], [], [], []
metrics = ['unitPrice','qty','sold','gross','sales','discount','points','prepaid','refund','refundQty']
for period in periods:
    for kind in (['상품별 조회(일자별)'] if period.startswith('2025') else ['상품별 조회(일자별)', '옵션별 조회(옵션별)']):
        files = [p for p in pathlib.Path('/Users/kimyeji/Downloads').glob('*.xlsx')
                 if period in p.name and kind in unicodedata.normalize('NFC', p.name)]
        assert len(files) == 1, files
        path = files[0]
        sheet = openpyxl.load_workbook(path, read_only=True, data_only=True).active
        rows = list(sheet.values)
        source = 'xlsx-' + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        start, end = period.split('~')
        info = dict(id=source, label=unicodedata.normalize('NFC', path.name), start=start, end=end,
                    sheet=sheet.title, kind='products' if kind.startswith('상품') else 'options',
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        records = []
        if info['kind'] == 'products':
            for rownum, row in enumerate(rows[7:], 8):
                values = dict(zip(metrics, row[3:]))
                if row[0] == '전체 합계':
                    info['declared'] = values
                elif row[0] == '부분 분할결제':
                    adjustments.append(dict(source=source, label=row[0], **values))
                elif str(row[0]).startswith('일자별 합계'):
                    totals.append(dict(date=row[2], source=source, partial=row[2]=='2026-10-28', **values))
                elif row[1]:
                    assert start <= row[2] <= end
                    records.append(dict(date=row[2], category=row[0], name=row[1],source=source,sourceRow=rownum,**values))
            daily = [r for r in totals if r['source'] == source]
            for d in daily:
                for key in ['qty','gross','sales','discount','points','prepaid','refund','refundQty']:
                    assert sum(r[key] or 0 for r in records if r['date']==d['date']) == d[key], (d,key)
            for key in ['qty','gross','sales','discount','points','prepaid','refund','refundQty']:
                assert sum(d[key] or 0 for d in daily) + sum(a[key] or 0 for a in adjustments if a['source']==source) == info['declared'][key], (source,key)
            info['days'] = len(daily)
            products += records
        else:
            for rownum,row in enumerate(rows[7:], 8):
                if not any(x is not None for x in row): continue
                assert row[0]=='이코복스 이태원점' and row[1] and row[3], row
                records.append(dict(store=row[0],option=row[1],category=row[2],name=row[3],unitPrice=row[4],
                    orderCount=row[5],selections=row[6],sales=row[7],averagePrice=row[8],selectionRate=row[9],
                    start=start,end=end,source=source,sourceRow=rownum))
            options += records
            info['selections'] = sum(r['selections'] for r in records)
            info['optionSales'] = sum(r['sales'] for r in records)
        info['records'] = len(records)
        sources.append(info)

# Replace the imported dates, retaining prior-year evidence and non-overlapping records.
coverage = {r['date'] for r in totals}
analysis['products'] = [r for r in analysis['products'] if r['date'] not in coverage] + products
analysis['productCoverage'] = sorted(set(analysis['productCoverage']) | coverage)
analysis['options'] = options
analysis['dailyProductTotals'] = totals
analysis['productAdjustments'] = adjustments
analysis['partialProductDates'] = ['2026-10-28']
analysis['importSources'] = sources
analysis['importRevision'] = '2026-10-28-seven-exports-v2'
(ROOT/'public/analysis-data.json').write_text(json.dumps(analysis, ensure_ascii=False, separators=(',',':')))
(ROOT/'reconciliations/2025-2026-product-import.json').write_text(json.dumps(dict(sources=sources,
    productRecords=len(products), optionRecords=len(options), days=len(coverage), adjustments=adjustments,
    method='Daily detail reconciles to each daily subtotal; subtotals plus split-payment adjustments reconcile to file totals. Options remain period-only rows and are never added to product revenue.'), ensure_ascii=False, indent=2))
print(json.dumps(dict(products=len(products),options=len(options),days=len(coverage),productSales=sum(r['sales'] for r in products),sources=sources),ensure_ascii=False))
