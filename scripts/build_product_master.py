"""Build explicit, reviewable display identities; keep every source row unchanged."""
import collections, hashlib, json, pathlib, re, unicodedata
ROOT=pathlib.Path(__file__).resolve().parents[1]
a=json.loads((ROOT/'dist/analysis-data.json').read_text())
def stem(name):
    n=unicodedata.normalize('NFKC',name).strip()
    n=re.sub(r'^\[\s*(?:마감\s*특가\s*)?\d+%\s*할인\s*\]\s*','',n)
    n=re.sub(r'\((?:HOT|ICE|ICED)(?:\s+ONLY)?\)|\(Only (?:Hot|Ice)\)|\((?:ICED ONL?|ICED O)\)?|\bICE\s*$','',n,flags=re.I).strip()
    n=re.sub(r'^(그로서리|맥주|화이트|레드|로제|스파클링)\s*\d*\s*_?\s+',r'\1 ',n)
    n=re.sub(r'^수제맥주\s*\)\s*','맥주 ',n)
    # English translations are presentation aliases. Preserve package sizes and sets.
    units=re.findall(r'\d+(?:\.\d+)?\s*(?:kg|g|ml|l|pcs|ea|인치)',n,flags=re.I)
    n=re.sub(r'\(?\d+(?:\.\d+)?\s*(?:kg|g|ml|l|pcs|ea|인치)\)?','',n,flags=re.I).strip()
    first_korean=re.search('[가-힣]',n)
    match=re.search(r'[A-Za-z]',n[first_korean.start():]) if first_korean else None
    if match:match_start=first_korean.start()+match.start()
    if match and re.search('[가-힣]',n[:match.start()]) and not re.search(r'\bor\b',n,re.I):
        n=n[:match_start].rstrip(' (')
    for unit in units:
        if re.sub(r'\s','',unit).lower() not in re.sub(r'\s','',n).lower():n+=' ('+unit.lower()+')'
    n=re.sub(r'\s+',' ',n).strip(' *')
    return n

# Only verified spelling/name aliases; different recipes, sizes and set contents remain distinct.
aliases={
 '수제바닐라라떼':'바닐라라떼','마시멜로솔트핫초코':'마쉬멜로솔트핫초코',
 '크로와상':'크루아상',
 '수재햄토마토파누쪼':'수제햄토마토파누쪼','시그니쳐피칸파이':'시그니처피칸파이',
 '애플사이다비니거':'애사비','아샷추':'아샷추',
 '스몰박스젤라또2가지맛(450g)':'스몰박스2가지맛(450g)',
 '미디엄박스젤라또3가지맛(650g)':'미디엄박스3가지맛(650g)',
 '라지박스젤라또4가지맛(900g)':'라지박스4가지맛(900g)',
 '캐모마일티':'캐모마일','페퍼민트티':'페퍼민트','얼그레이티':'얼그레이',
 '평션투블렌드원두':'펑션투블렌드원두',
 '평션투블렌드원두(200g)':'펑션투블렌드원두(200g)',
}
def identity(name):
    s=re.sub(r'\s','',stem(name)).lower()
    return aliases.get(s,s)

categories={'SPECIALTYCOFFEE':'스페셜티 커피','SpecialtyCoffee':'스페셜티 커피','Non Coffee':'논커피',
 'Bakery':'빵','Cake':'케이크','Dessert':'디저트','Dessert & Deli':'디저트',
 'Wine':'와인','Beer':'맥주','Wine & Beer':'주류',"Lorenzo's Pizza":'피자',
 'Gelato':'젤라또','IceCream':'아이스크림','Ice Cream':'아이스크림',
 'Cheese & Snack':'치즈 & 스낵','Grocery':'그로서리','Coffee Beans':'원두'}
groups=collections.defaultdict(list)
for r in a['products']:groups[identity(r['name'])].append(r)
master=[]
for key,rs in sorted(groups.items()):
    # A stable label/category across periods, independent of the selected date range.
    useful=[r for r in rs if r['category'] not in ['배달앱','미분류']]
    preferred=max(useful or rs,key=lambda r:(r['date'],len(r['name'])))
    label=stem(preferred['name'])
    canonical=aliases.get(re.sub(r'\s','',label).lower())
    if canonical:
        matches=[stem(r['name']) for r in rs if re.sub(r'\s','',stem(r['name'])).lower()==canonical]
        if matches:label=collections.Counter(matches).most_common(1)[0][0]
    names=sorted({r['name'] for r in rs})
    master.append(dict(id='product-'+hashlib.sha256(key.encode()).hexdigest()[:16],name=label,
        category=categories.get(preferred['category'],preferred['category']),
        aliases=names,originalCategories=sorted({r['category'] for r in rs})))
(ROOT/'dist/product-master.json').write_text(json.dumps(dict(revision='2026-10-28-v1',products=master),ensure_ascii=False,separators=(',',':')))
merged=[p for p in master if len(p['aliases'])>1 or len(p['originalCategories'])>1]
(ROOT/'reconciliations/product-groups.json').write_text(json.dumps(dict(originalPairs=len({(r['category'],r['name']) for r in a['products']}),products=len(master),mergedGroups=merged),ensure_ascii=False,indent=2))
print(json.dumps(dict(originalPairs=len({(r['category'],r['name']) for r in a['products']}),products=len(master),mergedGroups=len(merged)),ensure_ascii=False))
