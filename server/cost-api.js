import {validateCosts,emptyCosts} from '../public/cost-model.js';
const cookieName='ikovox_cost_session';
const json=(data,status=200,headers={})=>Response.json(data,{status,headers:{'Cache-Control':'no-store',...headers}});
const digest=async text=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))).map(x=>x.toString(16).padStart(2,'0')).join('');
const equal=(a,b)=>{if(typeof a!=='string'||typeof b!=='string'||a.length!==b.length)return false;let v=0;for(let i=0;i<a.length;i++)v|=a.charCodeAt(i)^b.charCodeAt(i);return v===0;};
async function sign(value,secret){const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign']);return Array.from(new Uint8Array(await crypto.subtle.sign('HMAC',key,new TextEncoder().encode(value)))).map(x=>x.toString(16).padStart(2,'0')).join('');}
async function authenticated(request,env){const token=request.headers.get('cookie')?.split(';').map(x=>x.trim()).find(x=>x.startsWith(cookieName+'='))?.slice(cookieName.length+1);if(!token||!env.COST_SESSION_SECRET)return false;const [expires,signature]=token.split('.');return Number(expires)>Date.now()&&Number(expires)<Date.now()+8*86400000&&equal(signature,await sign(expires,env.COST_SESSION_SECRET));}
async function body(request){const text=await request.text();if(new TextEncoder().encode(text).length>5e6)throw Error('자료는 5MB 이하로 저장해 주세요.');return JSON.parse(text);}
export async function handleCostRequest(request,env){
 const url=new URL(request.url);if(!url.pathname.startsWith('/api/costs'))return null;
 if(request.method!=='GET'&&request.headers.get('origin')!==url.origin)return json({error:'같은 홈페이지에서 요청해 주세요.'},403);
 if(!env.DB||!env.COST_PASSWORD_HASH||!env.COST_SESSION_SECRET)return json({error:'공유 저장소 설정을 확인해 주세요.'},503);
 try{
 if(url.pathname==='/api/costs/session'){
  if(request.method==='GET')return json({authenticated:await authenticated(request,env)});
  if(request.method==='DELETE')return json({ok:true},200,{'Set-Cookie':`${cookieName}=; Path=/api/costs; HttpOnly; Secure; SameSite=Strict; Max-Age=0`});
  if(request.method!=='POST')return json({error:'지원하지 않는 요청입니다.'},405);
  const ip=await digest((request.headers.get('cf-connecting-ip')||'unknown')+env.COST_SESSION_SECRET),window=Math.floor(Date.now()/60000),key=ip+':'+window;
  const count=await env.DB.prepare('INSERT INTO cost_login_attempts (bucket,attempts) VALUES (?,1) ON CONFLICT(bucket) DO UPDATE SET attempts=attempts+1 RETURNING attempts').bind(key).first();
  if(count.attempts>15)return json({error:'로그인 시도가 많습니다. 잠시 후 다시 시도해 주세요.'},429);
  const input=await body(request);if(typeof input.password!=='string'||!equal(await digest(input.password),env.COST_PASSWORD_HASH))return json({error:'관리 비밀번호를 확인해 주세요.'},401);
  const expires=String(Date.now()+7*86400000),token=expires+'.'+await sign(expires,env.COST_SESSION_SECRET);
  return json({ok:true},200,{'Set-Cookie':`${cookieName}=${token}; Path=/api/costs; HttpOnly; Secure; SameSite=Strict; Max-Age=604800`});
 }
 if(!await authenticated(request,env))return json({error:'관리 비밀번호로 로그인해 주세요.'},401);
 if(url.pathname==='/api/costs/history'&&request.method==='GET'){const rows=await env.DB.prepare('SELECT revision,updated_at FROM cost_history ORDER BY revision DESC LIMIT 30').all();return json({history:rows.results});}
 if(url.pathname==='/api/costs/history/restore'&&request.method==='POST'){
  const input=await body(request),saved=await env.DB.prepare('SELECT payload FROM cost_history WHERE revision=?').bind(input.revision).first();if(!saved)return json({error:'해당 백업을 찾지 못했습니다.'},404);
  return await saveState(env,JSON.parse(saved.payload),input.expectedRevision);
 }
 if(url.pathname!=='/api/costs')return json({error:'요청 경로가 올바르지 않습니다.'},404);
 if(request.method==='GET'){const row=await env.DB.prepare("SELECT payload,revision,updated_at FROM cost_records WHERE id='shared'").first();return json(row?{costs:JSON.parse(row.payload),revision:row.revision,updatedAt:row.updated_at}:{costs:emptyCosts(),revision:0,updatedAt:null});}
 if(request.method==='PUT'){const input=await body(request);return await saveState(env,input.costs,input.revision);}
 return json({error:'지원하지 않는 요청입니다.'},405);
 }catch(error){return json({error:error instanceof SyntaxError?'JSON 자료를 확인해 주세요.':error.message||'공유 자료를 처리하지 못했습니다.'},400);}
}
async function saveState(env,costs,revision){
 validateCosts(costs);if(!Number.isSafeInteger(revision)||revision<0)return json({error:'자료 버전을 확인해 주세요.'},400);
 const payload=JSON.stringify(costs);if(new TextEncoder().encode(payload).length>5e6)return json({error:'자료는 5MB 이하로 저장해 주세요.'},413);
 const previous=await env.DB.prepare("SELECT payload,revision FROM cost_records WHERE id='shared'").first();
 if((previous?.revision??0)!==revision)return json({error:'다른 기기에서 먼저 수정했습니다. 작성 내용은 이 브라우저에 보존했습니다. 최신 자료를 불러온 뒤 다시 수정해 주세요.'},409);
 if(previous){const old=JSON.parse(previous.payload);if((old.ingredients.length||old.recipes.length)&&!costs.ingredients.length&&!costs.recipes.length)return json({error:'빈 자료로 공유 자료 전체를 덮어쓸 수 없습니다.'},422);}
 const now=new Date().toISOString();let result;
 if(revision===0){result=await env.DB.prepare("INSERT OR IGNORE INTO cost_records (id,payload,revision,updated_at) VALUES ('shared',?,1,?) RETURNING revision").bind(payload,now).first();}
 else {const results=await env.DB.batch([
  env.DB.prepare("INSERT OR IGNORE INTO cost_history (revision,payload,updated_at) SELECT revision,payload,updated_at FROM cost_records WHERE id='shared' AND revision=?").bind(revision),
  env.DB.prepare("UPDATE cost_records SET payload=?,revision=revision+1,updated_at=? WHERE id='shared' AND revision=? RETURNING revision").bind(payload,now,revision)
 ]);result=results[1].results?.[0];}
 if(!result)return json({error:'다른 기기의 수정과 겹쳤습니다. 최신 자료를 다시 불러와 주세요.'},409);
 return json({revision:result.revision,updatedAt:now});
}
