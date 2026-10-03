const noCache = {'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'same-origin'};
const json = (v,status=200) => new Response(JSON.stringify(v),{status,headers:{...noCache,'Content-Type':'application/json; charset=utf-8'}});
let keysCache;
function decode(s){const padded=s.replace(/-/g,'+').replace(/_/g,'/');return Uint8Array.from(atob(padded),c=>c.charCodeAt(0))}
export async function verifyAccess(token,env,audience){
  if(!token || token.length>32768 || !audience || !/^[a-z0-9-]+\.cloudflareaccess\.com$/.test(env.ACCESS_TEAM_DOMAIN||''))return null;
  try{
    const parts=token.split('.');if(parts.length!==3)return null;
    const header=JSON.parse(new TextDecoder().decode(decode(parts[0])));
    const payload=JSON.parse(new TextDecoder().decode(decode(parts[1])));
    const issuer='https://'+env.ACCESS_TEAM_DOMAIN;
    const now=Math.floor(Date.now()/1000);
    if(header.alg!=='RS256'||!header.kid||payload.iss!==issuer||typeof payload.exp!=='number'||payload.exp<=now||(payload.nbf&&payload.nbf>now+60))return null;
    const aud=Array.isArray(payload.aud)?payload.aud:[payload.aud];if(!aud.includes(audience))return null;
    if(!keysCache||keysCache.issuer!==issuer||keysCache.expires<Date.now()){
      const r=await fetch(issuer+'/cdn-cgi/access/certs');if(!r.ok)return null;
      keysCache={issuer,keys:(await r.json()).keys,expires:Date.now()+3600000};
    }
    let jwk=keysCache.keys.find(k=>k.kid===header.kid&&k.kty==='RSA');
    if(!jwk){keysCache=undefined;return null}
    const key=await crypto.subtle.importKey('jwk',jwk,{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['verify']);
    const valid=await crypto.subtle.verify('RSASSA-PKCS1-v1_5',key,decode(parts[2]),new TextEncoder().encode(parts[0]+'.'+parts[1]));
    return valid?payload:null;
  }catch{return null}
}
export default {async fetch(request,env){
  const url=new URL(request.url);
  if(!env.ACCESS_TEAM_DOMAIN||!env.ACCESS_AUD||!env.ALLOWED_EMAIL||!env.RESULTS)return json({error:'私人網站尚未完成設定'},503);
  const upload=url.pathname==='/_update';
  const token=request.headers.get('Cf-Access-Jwt-Assertion');
  const claims=await verifyAccess(token,env,upload?env.UPDATE_ACCESS_AUD:env.ACCESS_AUD);
  if(!claims)return json({error:'請透過 Cloudflare Access 登入'},401);
  if(upload){
    if(request.method!=='PUT')return json({error:'只接受更新請求'},405);
    if(!env.UPDATE_SECRET||request.headers.get('Authorization')!=='Bearer '+env.UPDATE_SECRET)return json({error:'更新授權失敗'},403);
    if(request.headers.get('Content-Type')?.split(';')[0]!=='application/json')return json({error:'資料格式錯誤'},415);
    const raw=await request.arrayBuffer();if(raw.byteLength>4*1024*1024)return json({error:'資料過大'},413);
    let value;try{value=JSON.parse(new TextDecoder().decode(raw))}catch{return json({error:'資料格式錯誤'},400)}
    const d=value.data;if(!d||!Array.isArray(d.results)||!Number.isFinite(Date.parse(d.updatedAt))||!/^\d{4}-\d{2}-\d{2}$/.test(d.date))return json({error:'掃描欄位不足'},400);
    const prior=await env.RESULTS.prepare('SELECT updated_at FROM state_chunks ORDER BY idx LIMIT 1').first();
    if(prior&&Date.parse(prior.updated_at)>Date.parse(d.updatedAt))return json({error:'拒絕覆蓋較新的結果'},409);
    const text=new TextDecoder().decode(raw);
    const statements=[env.RESULTS.prepare('DELETE FROM state_chunks')];
    for(let start=0,index=0;start<text.length;start+=131072,index++){
      statements.push(env.RESULTS.prepare('INSERT INTO state_chunks (idx, data, updated_at) VALUES (?, ?, ?)').bind(index,text.slice(start,start+131072),d.updatedAt));
    }
    await env.RESULTS.batch(statements);
    return json({saved:true,date:d.date});
  }
  if(typeof claims.email!=='string'||claims.email.toLowerCase()!==env.ALLOWED_EMAIL.toLowerCase())return json({error:'此帳號沒有存取權'},403);
  if(request.method!=='GET'&&request.method!=='HEAD')return json({error:'請從私人 GitHub Actions 觸發掃描'},405);
  if(url.pathname==='/api/state'){
    const rows=await env.RESULTS.prepare('SELECT data FROM state_chunks ORDER BY idx').all();
    if(!rows.results.length)return json({state:{running:false,done:0,total:0,errors:[]},config:{},data:null});
    return new Response(request.method==='HEAD'?null:rows.results.map(r=>r.data).join(''),{headers:{...noCache,'Content-Type':'application/json; charset=utf-8'}});
  }
  if(url.pathname.startsWith('/api/')||url.pathname==='/state.json')return json({error:'找不到資料'},404);
  const response=await env.ASSETS.fetch(request);
  const protectedResponse=new Response(response.body,response);
  for(const [key,value] of Object.entries(noCache))protectedResponse.headers.set(key,value);
  return protectedResponse;
}};
