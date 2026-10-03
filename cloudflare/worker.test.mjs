import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import worker,{verifyAccess} from './worker.mjs';
if(!globalThis.crypto)Object.defineProperty(globalThis,'crypto',{value:webcrypto});
const pair=await crypto.subtle.generateKey({name:'RSASSA-PKCS1-v1_5',modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:'SHA-256'},true,['sign','verify']);
const jwk=await crypto.subtle.exportKey('jwk',pair.publicKey);jwk.kid='test-key';
globalThis.fetch=async()=>Response.json({keys:[jwk]});
const env={ACCESS_TEAM_DOMAIN:'unit-test.cloudflareaccess.com',ACCESS_AUD:'user-aud',UPDATE_ACCESS_AUD:'service-aud',ALLOWED_EMAIL:'owner@example.com',RESULTS:{prepare(){return {all:async()=>({results:[]})}}},ASSETS:{fetch:async()=>new Response('private page')}};
const enc=obj=>Buffer.from(JSON.stringify(obj)).toString('base64url');
async function jwt(extra={}){const payload={iss:'https://'+env.ACCESS_TEAM_DOMAIN,aud:['user-aud'],email:'owner@example.com',exp:Math.floor(Date.now()/1000)+300,...extra};const parts=enc({alg:'RS256',kid:jwk.kid})+'.'+enc(payload);const sig=await crypto.subtle.sign('RSASSA-PKCS1-v1_5',pair.privateKey,new TextEncoder().encode(parts));return parts+'.'+Buffer.from(sig).toString('base64url')}
test('missing setup denies all content',async()=>assert.equal((await worker.fetch(new Request('https://test/'),{})).status,503));
test('unauthenticated page and data both denied',async()=>{for(const path of ['/','/api/state','/guide.html','/state.json'])assert.equal((await worker.fetch(new Request('https://test'+path),env)).status,401)});
test('signed owner token allows content and is not cacheable',async()=>{const r=await worker.fetch(new Request('https://test/',{headers:{'Cf-Access-Jwt-Assertion':await jwt()}}),env);assert.equal(r.status,200);assert.equal(r.headers.get('Cache-Control'),'private, no-store')});
test('wrong email denied despite valid Access signature',async()=>assert.equal((await worker.fetch(new Request('https://test/',{headers:{'Cf-Access-Jwt-Assertion':await jwt({email:'other@example.com'})}}),env)).status,403));
test('expired, wrong audience, and altered JWTs denied',async()=>{assert.equal(await verifyAccess(await jwt({exp:1}),env,'user-aud'),null);assert.equal(await verifyAccess(await jwt({aud:['wrong']}),env,'user-aud'),null);assert.equal(await verifyAccess((await jwt())+'x',env,'user-aud'),null)});
test('browser token cannot write data',async()=>assert.equal((await worker.fetch(new Request('https://test/_update',{method:'PUT',headers:{'Cf-Access-Jwt-Assertion':await jwt()}}),env)).status,401));
