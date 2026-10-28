// Source records are immutable; the catalog supplies one shared analysis identity.
export function createProductCatalog(master) {
  const byName=new Map(),byId=new Map(),cache=new WeakMap();
  for(const p of master.products){byId.set(p.id,p);for(const n of p.aliases)byName.set(n,p)}
  const resolve=r=>byName.get(r.originalName??r.name)||{id:JSON.stringify(['unmapped',r.name.trim()]),name:r.name.trim(),category:r.category,aliases:[r.name],originalCategories:[r.category]};
  const row=r=>{if(cache.has(r))return cache.get(r);const p=resolve(r),value={...r,productId:p.id,name:p.name,category:p.category,originalName:r.originalName??r.name,originalCategory:r.originalCategory??r.category};cache.set(r,value);return value};
  const key=r=>r.productId||resolve(r).id;
  const storedKey=k=>{if(byId.has(k))return k;try{const [category,name]=JSON.parse(k);if(typeof name==='string')return resolve({category,name}).id}catch{}return k};
  return {row,key,storedKey,resolve,get:id=>byId.get(id),products:master.products};
}
