import assert from 'node:assert/strict';
import {emptyCosts,validateCosts,unitCost,recipeCost,mergeCostIngredients,recipeSaleStatus,matchesCostRecipe,groupCostRecipes,summarizeRecipeRates} from '../dist/cost-model.js';
const i={id:'butter',name:'버터',unit:'kg',packQty:1,price:18000,yield:1,supplier:'',note:''};
const r={id:'bake',name:'베이커리',category:'베이커리',output:20,salePrice:4000,target:.1,note:'',lines:[{ingredientId:'butter',qty:500}]};
validateCosts({version:1,ingredients:[i],recipes:[r]});
assert.equal(unitCost(i),18);
assert.equal(recipeCost(r,[i]).total,9000);
assert.equal(recipeCost(r,[i]).perUnit,450);
assert.equal(recipeCost(r,[i]).rate,.1125);
assert.equal(recipeCost(r,[i]).overTarget,true);
assert.equal(recipeCost(r,[{...i,price:24000}]).perUnit,600);
assert.equal(recipeCost(r,[{...i,yield:.8}]).perUnit,562.5);
assert.equal(unitCost({...i,unit:'L'}),18);
assert.equal(unitCost({...i,unit:'개',packQty:50,price:5000}),100);
assert.equal(unitCost({...i,unit:'샷',packQty:1,price:300}),300);
assert.equal(unitCost({...i,unit:'잔',packQty:50,price:42900}),858);
validateCosts({version:1,ingredients:[{...i,unit:'샷'}],recipes:[]});
validateCosts({version:1,ingredients:[{...i,unit:'잔'}],recipes:[]});
assert.equal(recipeCost(r,[{...i,price:null}]).perUnit,null);
assert.equal(recipeCost(r,[{...i,price:0}]).perUnit,0);
assert.equal(recipeCost({...r,salePrice:null},[i]).rate,null);
assert.equal(recipeCost({...r,output:1},[i]).perUnit,9000);
assert.equal(recipeCost(r,[]).missing.length,1);
for(const patch of [{packQty:0},{unit:'toString'},{price:-1},{yield:0},{yield:1.1},{price:Infinity}])assert.throws(()=>validateCosts({version:1,ingredients:[{...i,...patch}],recipes:[]}));
assert.throws(()=>validateCosts({version:1,ingredients:[i,i],recipes:[]}));
for(const patch of [{output:0},{target:1.1},{salePrice:0},{lines:[]},{lines:[{ingredientId:'absent',qty:1}]},{lines:[{ingredientId:i.id,qty:1},{ingredientId:i.id,qty:2}]}])assert.throws(()=>validateCosts({version:1,ingredients:[i],recipes:[{...r,...patch}]}));
assert.deepEqual(validateCosts(JSON.parse(JSON.stringify({version:1,ingredients:[i],recipes:[r]}))),{version:1,ingredients:[i],recipes:[r]});
validateCosts(emptyCosts());
assert.equal(recipeSaleStatus(r),'판매중','Legacy recipes remain readable');
const coffee={...r,category:'음료',subcategory:'커피',salesStatus:'단종'};
validateCosts({version:1,ingredients:[i],recipes:[coffee]});
assert.equal(matchesCostRecipe(coffee,{category:'음료',subcategory:'커피',salesStatus:'단종'}),true);
assert.equal(matchesCostRecipe(coffee,{subcategory:'논커피'}),false);
assert.equal(matchesCostRecipe(coffee,{salesStatus:'판매중'}),false);
assert.equal(matchesCostRecipe(r,{subcategory:'__unset__',salesStatus:'판매중'}),true);
assert.equal(recipeCost(coffee,[i]).perUnit,recipeCost(r,[i]).perUnit,'Discontinued recipes keep their costs');
for(const patch of [{subcategory:'쿠키'},{salesStatus:'판매불명'}])assert.throws(()=>validateCosts({version:1,ingredients:[i],recipes:[{...coffee,...patch}]}));
const saved=JSON.parse(JSON.stringify({version:1,ingredients:[i],recipes:[coffee]}));
assert.deepEqual(validateCosts(saved).recipes[0],coffee,'Backup keeps classification and sales status');
assert.equal(mergeCostIngredients(saved,emptyCosts()).state.recipes[0].salesStatus,'단종');
const groupFixtures=[
 {...coffee,id:'retired',salePrice:100},
 {...coffee,id:'high',name:'라떼',salesStatus:'판매중',salePrice:6000},
 {...coffee,id:'missing',name:'가격 미입력',salesStatus:'판매중',salePrice:null},
 {...coffee,id:'low',name:'아메리카노',salesStatus:'판매중',salePrice:4000},
 {...coffee,id:'noncoffee',subcategory:'논커피',salesStatus:'판매중',salePrice:1000},
 {...r,id:'bakery',subcategory:'쿠키',salePrice:2000},
 {...r,id:'dessert',category:'디저트',subcategory:'케이크',salePrice:3000},
 {...coffee,id:'unset',subcategory:'',salesStatus:'판매중',salePrice:500}
];
const untouched=JSON.stringify(groupFixtures),groups=groupCostRecipes(groupFixtures);
assert.deepEqual(groups.map(g=>g.salesStatus),['판매중','단종']);
assert.deepEqual(groups[0].categories.map(c=>c.name),['음료','디저트','베이커리']);
assert.deepEqual(groups[0].categories[0].subcategories.map(s=>s.name),['커피','논커피','세분류 미지정']);
assert.deepEqual(groups[0].categories[0].subcategories[0].recipes.map(r=>r.id),['low','high','missing']);
assert.equal(groups.at(-1).categories[0].subcategories[0].recipes[0].id,'retired','Cheapest discontinued menu remains below active menus');
assert.equal(JSON.stringify(groupFixtures),untouched,'Display ordering must not mutate saved records');
assert.equal(groupCostRecipes(groupFixtures.filter(r=>matchesCostRecipe(r,{salesStatus:'단종'}))).length,1);
assert.deepEqual(groupCostRecipes([]),[]);
const rateSummary=summarizeRecipeRates([{...r,salePrice:4500},{...r,salePrice:9000},{...r,salePrice:null}],[i]);
assert.ok(Math.abs(rateSummary.rate-.075)<1e-12);assert.equal(rateSummary.count,2);assert.equal(rateSummary.excluded,1);
assert.deepEqual(summarizeRecipeRates([r],[{...i,price:null}]),{rate:null,count:0,excluded:1});
assert.deepEqual(summarizeRecipeRates([r],[{...i,price:0}]),{rate:0,count:1,excluded:0});
assert.deepEqual(summarizeRecipeRates([],[]),{rate:null,count:0,excluded:0});
assert.equal(summarizeRecipeRates([{...r,salePrice:4500}],[i]).rate,.1,'Filtering changes the visible group average');
assert.equal(summarizeRecipeRates([r],[{...i,price:36000}]).rate,recipeCost(r,[i]).rate*2,'Ingredient price updates affect averages');
const existing={version:1,ingredients:[{...i,name:'초코베이스'}],recipes:[r]};
const incoming={version:1,ingredients:[{...i,id:'same-name',name:'초코 베이스',price:99999},{...i,name:'새 재료'}],recipes:[]};
const merged=mergeCostIngredients(existing,incoming,()=> 'new-id');
assert.equal(merged.added,1);assert.equal(merged.skipped.length,1);
assert.equal(merged.state.ingredients[0].price,18000);
assert.equal(merged.state.ingredients[1].id,'new-id');
assert.deepEqual(merged.state.recipes,existing.recipes);
assert.equal(existing.ingredients.length,1,'Merge must not mutate existing data');
assert.equal(mergeCostIngredients(merged.state,incoming).added,0,'Repeat import must not duplicate ingredients');
assert.throws(()=>mergeCostIngredients(existing,{...incoming,ingredients:[{...i,price:-1}]}));
console.log('Cost checks passed: unit conversion, batch yields, price updates, loss allowance, missing versus zero prices, invalid and duplicate records, backup round-trip.');
