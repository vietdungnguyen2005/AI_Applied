import {expect,it} from "vitest";
import worker from "../src/worker";
import {TestDatabase} from "./database";
import {publicKeys,signed} from "./sign";
import type {AiBinding} from "../src/spec";
const scopes=["4aa83e9f-0a0a-5558-8f5e-0f87db27c923"];
export async function control(DB:TestDatabase,run:string,body:unknown,updates:Record<string,unknown>={},AI?:AiBinding){
  return worker.fetch(signed("/ai/runs/control",JSON.stringify(body),{operation:"run_control",run_id:run,...updates}),{PUBLIC_KEYS_JSON:publicKeys,DB,AI});
}
export async function start(DB:TestDatabase,run=crypto.randomUUID()){
  const result=await control(DB,run,{action:"start",question:"List import jobs",conversation_id:crypto.randomUUID(),collection_ids:scopes});
  expect(result.status).toBe(200);return run;
}
it("creates a durable actor-owned investigation using the existing RunSnapshot contract",async()=>{
  const run=crypto.randomUUID(),conversation=crypto.randomUUID(),DB=new TestDatabase();
  const result=await worker.fetch(signed("/ai/runs/control",JSON.stringify({action:"start",question:"List import jobs",
    conversation_id:conversation,collection_ids:scopes}),{operation:"run_control",run_id:run}),{PUBLIC_KEYS_JSON:publicKeys,DB});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({state:{run_id:run,conversation_id:conversation,status:"started",phase:"idle",
    revision:0,step:0,can_resume:true,can_cancel:true,observations:[]},collection_ids:scopes,pending_intent:null,lease_id:null,known_job_ids:[]});
});
it("persists a model-selected read intent before any business read is allowed",async()=>{
  const DB=new TestDatabase(),run=await start(DB);
  const AI={async run(){return {response:JSON.stringify({tool_name:"get_imports",job_id:"",query:""})};}};
  const result=await control(DB,run,{action:"plan",expected_revision:0},{},AI);
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({state:{status:"started",phase:"ready",revision:2,step:0},
    pending_intent:{tool_name:"get_imports",arguments:{}},lease_id:null});
});
export async function ready(DB:TestDatabase){
  const run=await start(DB),AI={async run(){return {response:JSON.stringify({tool_name:"get_imports",job_id:"",query:""})};}};
  expect((await control(DB,run,{action:"plan",expected_revision:0},{},AI)).status).toBe(200);return run;
}
it("permits only one concurrent claim for a ready read",async()=>{
  const DB=new TestDatabase(),run=await ready(DB);
  const results=await Promise.all([control(DB,run,{action:"claim",expected_revision:2}),control(DB,run,{action:"claim",expected_revision:2})]);
  expect(results.map(r=>r.status).sort()).toEqual([200,409]);
  const body=await results.find(r=>r.status===200)!.json();
  expect(body).toMatchObject({state:{phase:"executing",revision:3},pending_intent:{tool_name:"get_imports"}});
  expect(body.lease_id).toMatch(/^[0-9a-f-]{36}$/);
});
it("records an observation only under the current lease and advances one step",async()=>{
  const DB=new TestDatabase(),run=await ready(DB);
  const claimed=await (await control(DB,run,{action:"claim",expected_revision:2})).json();
  const observation={call_id:claimed.pending_intent.call_id,tool_name:"get_imports",status:"ok",observed_at:new Date().toISOString(),
    truncated:false,data:{imports:[]},error_code:null};
  const bad=await control(DB,run,{action:"record",expected_revision:3,lease_id:crypto.randomUUID(),observation});
  expect(bad.status).toBe(409);
  const result=await control(DB,run,{action:"record",expected_revision:3,lease_id:claimed.lease_id,observation});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({state:{phase:"idle",step:1,revision:4,observations:[{tool_name:"get_imports",item_count:0}]},lease_id:null,pending_intent:null});
});
it("marks an interrupted read unknown and recovers without dispatching that read again",async()=>{
  const DB=new TestDatabase(),run=await ready(DB);
  const claimed=await (await control(DB,run,{action:"claim",expected_revision:2})).json();
  DB.raw.exec("UPDATE runs SET revision=4,payload=json_set(payload,'$.revision',4,'$.lease_until',1)");
  const inspected=await (await control(DB,run,{action:"inspect"})).json();
  expect(inspected).toMatchObject({state:{status:"waiting_for_operator",phase:"executing",reason:"OUTCOME_UNKNOWN",revision:5,can_resume:true}});
  const recovered=await control(DB,run,{action:"recover",expected_revision:5});
  expect(recovered.status).toBe(200);
  expect(await recovered.json()).toMatchObject({state:{status:"started",phase:"idle",step:1,observations:[{
    call_id:claimed.pending_intent.call_id,status:"unavailable",error_code:"UPSTREAM_UNAVAILABLE"}]},pending_intent:null});
});
it("finishes with metadata derived from recorded observations rather than model-written facts",async()=>{
  const DB=new TestDatabase(),run=await ready(DB);
  const claimed=await (await control(DB,run,{action:"claim",expected_revision:2})).json();
  await control(DB,run,{action:"record",expected_revision:3,lease_id:claimed.lease_id,observation:{call_id:claimed.pending_intent.call_id,
    tool_name:"get_imports",status:"ok",observed_at:new Date().toISOString(),truncated:false,data:{imports:[]},error_code:null}});
  const AI={async run(){return {response:JSON.stringify({tool_name:"stop",job_id:"",query:""})};}};
  const result=await control(DB,run,{action:"plan",expected_revision:4},{step:1},AI);
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({state:{status:"completed",phase:"terminal",step:1,revision:6,
    outcome:{kind:"final",status:"answered",handoff_reason:null}}});
});
it("rejects duplicate run IDs and caps active slots per actor",async()=>{
  const DB=new TestDatabase(),run=await start(DB);
  const duplicate=await control(DB,run,{action:"start",question:"Again",conversation_id:crypto.randomUUID(),collection_ids:scopes});
  expect(duplicate.status).toBe(409);
  for(let i=1;i<8;i++)await start(DB);
  const result=await control(DB,crypto.randomUUID(),{action:"start",question:"Overflow",conversation_id:crypto.randomUUID(),collection_ids:scopes});
  expect(result.status).toBe(429);
});
it("reclaims expired active slots before admitting a fresh run",async()=>{
  const DB=new TestDatabase();for(let i=0;i<8;i++)await start(DB);
  DB.raw.exec("UPDATE runs SET expires_at=0,revision=revision+1,payload=json_set(payload,'$.expires_at',0,'$.revision',1)");
  expect((await control(DB,crypto.randomUUID(),{action:"start",question:"Fresh",conversation_id:crypto.randomUUID(),collection_ids:scopes})).status).toBe(200);
});
it("stops a run that exhausts its state-transition budget",async()=>{
  const DB=new TestDatabase(),run=await start(DB);
  DB.raw.exec("UPDATE runs SET revision=24,payload=json_set(payload,'$.revision',24)");
  const result=await control(DB,run,{action:"plan",expected_revision:24});
  expect(result.status).toBe(429);
  const inspected=await (await control(DB,run,{action:"inspect"})).json();
  expect(inspected).toMatchObject({state:{status:"failed",reason:"BUDGET_EXCEEDED"}});
});
it("allows inspection by the owner and hides the run from another actor",async()=>{
  const DB=new TestDatabase(),run=await start(DB);
  expect((await control(DB,run,{action:"inspect"})).status).toBe(200);
  expect((await control(DB,run,{action:"inspect"},{actor_ref:"b".repeat(64)})).status).toBe(404);
});
it("cancels exactly once with compare-and-swap revision and atomic metadata audit",async()=>{
  const DB=new TestDatabase(),run=await start(DB);
  const result=await control(DB,run,{action:"cancel",expected_revision:0});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({state:{status:"cancelled",phase:"terminal",revision:1,can_cancel:false,can_resume:false}});
  expect((await control(DB,run,{action:"cancel",expected_revision:0})).status).toBe(409);
  expect(DB.raw.prepare("SELECT kind FROM run_events ORDER BY revision").all()).toEqual([{kind:"start"},{kind:"cancel"}]);
});
it("expires an old run and scrubs its question and observations before inspection",async()=>{
  const DB=new TestDatabase(),run=await start(DB);
  DB.raw.prepare("UPDATE runs SET expires_at=0,payload=json_set(payload,'$.expires_at',0,'$.revision',1),revision=revision+1").run();
  const result=await control(DB,run,{action:"inspect"});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({state:{status:"expired",reason:"TTL_EXPIRED",can_resume:false,observations:[]}});
  const stored=DB.raw.prepare("SELECT payload FROM runs").get() as {payload:string};
  expect(JSON.parse(stored.payload).question).toBe("");
});
it("durably completes a mutation request as a human handoff without executing business changes",async()=>{
  const DB=new TestDatabase(),run=crypto.randomUUID();
  expect((await control(DB,run,{action:"start",question:"Activate the profile",conversation_id:crypto.randomUUID(),collection_ids:scopes})).status).toBe(200);
  const result=await control(DB,run,{action:"plan",expected_revision:0});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({state:{status:"waiting_for_operator",phase:"terminal",revision:2,
    reason:"BUSINESS_HANDOFF",can_resume:false,outcome:{kind:"handoff",status:"human_action_required"}}});
});
