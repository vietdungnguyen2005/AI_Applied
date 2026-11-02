import {expect,it} from "vitest";
import worker from "../src/worker";
import {publicKeys,signed} from "./sign";
import {TestDatabase} from "./database";
const scope="4aa83e9f-0a0a-5558-8f5e-0f87db27c923";
export const ask=()=>signed("/ai/ask",JSON.stringify({question:"Is a draft approval?",language:"en",collection_ids:[scope]}));
export function corpus(){
  const db=new TestDatabase(),id="22222222-2222-2222-2222-222222222222";
  db.raw.prepare("INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?,?)").run(id,scope,id,id,"approval",
    "A draft is not approval.","2026-10-01",null,1);
  return {db,id};
}
it("abstains without inference when the authorized corpus is empty",async()=>{
  const result=await worker.fetch(ask(),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase()});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({status:"abstained",answer:null,reason:"NO_SUPPORTED_EVIDENCE",
    citations:[],confidence:"unknown",provider_mode:"live"});
});
it("returns only an exact complete sentence from an authorized current chunk",async()=>{
  const {db,id}=corpus();
  let calls=0;
  const AI={async run(_model:string,_input:Record<string,unknown>){calls++;return {response:JSON.stringify({decision:"answer",
    claims:[{chunk_id:id,quote:"A draft is not approval."}]})};}};
  const result=await worker.fetch(ask(),{PUBLIC_KEYS_JSON:publicKeys,DB:db,AI});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({status:"answered",answer:"A draft is not approval.",confidence:"low",
    provider_mode:"live",citations:[{chunk_id:id}]});
  expect(calls).toBe(1);
});
it("refuses model calls after the durable global daily quota is consumed",async()=>{
  const {db}=corpus();
  db.raw.exec("CREATE TABLE IF NOT EXISTS budgets(bucket TEXT PRIMARY KEY,used INTEGER NOT NULL)");
  db.raw.prepare("INSERT INTO budgets VALUES(?,?)").run("daily:"+new Date().toISOString().slice(0,10),60);
  let calls=0;
  const AI={async run(){calls++;return {};}};
  const result=await worker.fetch(ask(),{PUBLIC_KEYS_JSON:publicKeys,DB:db,AI});
  expect(result.status).toBe(429);
  expect(calls).toBe(0);
});
it("rejects a model quote that drops a source sentence qualifier",async()=>{
  const {db,id}=corpus();
  const AI={async run(){return {response:JSON.stringify({decision:"answer",claims:[{chunk_id:id,quote:"draft is not approval."}]})};}};
  const result=await worker.fetch(ask(),{PUBLIC_KEYS_JSON:publicKeys,DB:db,AI});
  expect(result.status).toBe(502);
});
it("enforces the per-actor minute quota even while the daily quota remains available",async()=>{
  const {db}=corpus();
  db.raw.prepare("INSERT INTO budgets VALUES(?,?)").run("minute:"+Math.floor(Date.now()/60000)+":"+"a".repeat(64),4);
  let calls=0;const AI={async run(){calls++;return {};}};
  const result=await worker.fetch(ask(),{PUBLIC_KEYS_JSON:publicKeys,DB:db,AI});
  expect(result.status).toBe(429);expect(calls).toBe(0);
});
it("refuses an answer citing a topic with conflicting current source statements",async()=>{
  const {db,id}=corpus();
  const other="33333333-3333-3333-3333-333333333333";
  db.raw.prepare("INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?,?)").run(other,scope,other,other,"approval",
    "A draft counts as approval.","2026-10-01",null,1);
  const AI={async run(){return {response:JSON.stringify({decision:"answer",claims:[{chunk_id:id,quote:"A draft is not approval."}]})};}};
  const result=await worker.fetch(ask(),{PUBLIC_KEYS_JSON:publicKeys,DB:db,AI});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({status:"abstained",reason:"CONFLICTING_EVIDENCE",answer:null});
});
it("returns a deadline error for inference that does not finish within the signed deadline",async()=>{
  const {db}=corpus();
  const now=Math.floor(Date.now()/1000);
  const request=signed("/ai/ask",JSON.stringify({question:"Is a draft approval?",language:"en",collection_ids:[scope]}),
    {deadline_at:new Date((now+2)*1000).toISOString(),expires_at:now+2});
  const AI={async run(){return new Promise(()=>{});}};
  const result=await worker.fetch(request,{PUBLIC_KEYS_JSON:publicKeys,DB:db,AI});
  expect(result.status).toBe(504);
},4000);
it("does not return a citation withdrawn while inference was running",async()=>{
  const {db,id}=corpus();
  const AI={async run(){db.raw.prepare("UPDATE chunks SET active=0 WHERE chunk_id=?").run(id);
    return {response:JSON.stringify({decision:"answer",claims:[{chunk_id:id,quote:"A draft is not approval."}]})};}};
  const result=await worker.fetch(ask(),{PUBLIC_KEYS_JSON:publicKeys,DB:db,AI});
  expect(result.status).toBe(409);
});
