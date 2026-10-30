export const emptyCosts=()=>({version:1,ingredients:[],recipes:[]});
export const costUnits={g:{base:'g',factor:1},kg:{base:'g',factor:1000},ml:{base:'ml',factor:1},L:{base:'ml',factor:1000},'개':{base:'개',factor:1}};
const finite=n=>typeof n==='number'&&Number.isFinite(n);
export function validateCosts(s){
 if(!s||s.version!==1||!Array.isArray(s.ingredients)||!Array.isArray(s.recipes)||s.ingredients.length>5000||s.recipes.length>5000)throw Error('원가 자료 형식을 확인해 주세요.');
 const ids=new Set();const text=(v,max)=>typeof v==='string'&&v.length<=max;
 for(const i of s.ingredients){if(!text(i.id,100)||!i.id||ids.has(i.id)||!text(i.name,200)||!i.name.trim()||!Object.hasOwn(costUnits,i.unit)||!finite(i.packQty)||i.packQty<=0||!(i.price===null||(finite(i.price)&&i.price>=0))||!finite(i.yield)||i.yield<=0||i.yield>1||!text(i.supplier,300)||!text(i.note,1000))throw Error('재료의 이름·수량·단가·사용 가능 비율을 확인해 주세요.');ids.add(i.id);}
 const recipes=new Set();
 for(const r of s.recipes){if(!text(r.id,100)||!r.id||recipes.has(r.id)||!text(r.name,200)||!r.name.trim()||!['음료','디저트','베이커리'].includes(r.category)||!finite(r.output)||r.output<=0||!(r.salePrice===null||(finite(r.salePrice)&&r.salePrice>0))||!(r.target===null||(finite(r.target)&&r.target>0&&r.target<=1))||!text(r.note,1000)||!Array.isArray(r.lines)||r.lines.length===0||r.lines.length>200)throw Error('레시피의 이름·판매 가능 수량·판매가·재료를 확인해 주세요.');
  if(new Set(r.lines.map(l=>l.ingredientId)).size!==r.lines.length)throw Error('레시피에 같은 재료가 두 번 있습니다. 사용량을 합쳐 주세요.');
  for(const l of r.lines)if(!ids.has(l.ingredientId)||!finite(l.qty)||l.qty<0)throw Error('레시피의 재료와 사용량을 확인해 주세요.');recipes.add(r.id);
 }return s;
}
export function unitCost(i){return i.price===null?null:i.price/(i.packQty*costUnits[i.unit].factor*i.yield);}
export function recipeCost(r,ingredients){
 const map=new Map(ingredients.map(i=>[i.id,i]));
 const lines=r.lines.map(l=>{const i=map.get(l.ingredientId);const unit=i?unitCost(i):null;return {...l,ingredient:i,unit,cost:unit===null?null:unit*l.qty};});
 const missing=lines.filter(l=>l.cost===null);
 const total=missing.length||!lines.length?null:lines.reduce((n,l)=>n+l.cost,0);
 const perUnit=total===null?null:total/r.output;
 const rate=perUnit===null||r.salePrice===null?null:perUnit/r.salePrice;
 return {lines,missing,total,perUnit,rate,difference:rate===null?null:r.salePrice-perUnit,overTarget:rate!==null&&r.target!==null&&rate>r.target};
}
