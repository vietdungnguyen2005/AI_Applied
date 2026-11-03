import {expect,it} from "vitest";
import worker from "../src/worker";
import {TestDatabase} from "./database";
import {publicKeys,signed} from "./sign";
export function agentRequest(question:string,other:Record<string,unknown>={}){
  const request_id=crypto.randomUUID(),run_id=crypto.randomUUID(),step=0;
  return signed("/ai/agent/step",JSON.stringify({protocol_version:1,request_id,run_id,step,question,
    collection_ids:[],tool_result:null,previous_results:[],...other}),{request_id,run_id,step,operation:"agent_step",collection_ids:[]});
}
it("hands business mutations back to the operator without inference or a write tool",async()=>{
  const result=await worker.fetch(agentRequest("Activate this integration profile"),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase()});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({kind:"handoff",status:"human_action_required",handoff_reason:"OTHER_BUSINESS_MUTATION",citations:[]});
});
it("uses the live model only to select an allowlisted read intent",async()=>{
  const AI={async run(){return {response:JSON.stringify({tool_name:"get_imports",job_id:"",query:""})};}};
  const result=await worker.fetch(agentRequest("List current import jobs"),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase(),AI});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({kind:"tool_intent",intent:{tool_name:"get_imports",arguments:{}}});
});
it("rejects an invented job ID even when it is syntactically valid",async()=>{
  const AI={async run(){return {response:JSON.stringify({tool_name:"inspect_import_job",job_id:crypto.randomUUID(),query:""})};}};
  const result=await worker.fetch(agentRequest("Inspect the latest import"),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase(),AI});
  expect(result.status).toBe(502);
});
it("finishes from an existing observation when the model repeats the same list read",async()=>{
  const request_id=crypto.randomUUID(),run_id=crypto.randomUUID(),DB=new TestDatabase();
  const payload={protocol_version:1,request_id,run_id,step:1,question:"List current import jobs",collection_ids:[],previous_results:[],
    tool_result:{call_id:crypto.randomUUID(),tool_name:"get_imports",status:"ok",observed_at:new Date().toISOString(),truncated:false,data:{imports:[]},error_code:null}};
  const AI={async run(){return {response:JSON.stringify({tool_name:"get_imports",job_id:"",query:""})};}};
  const result=await worker.fetch(signed("/ai/agent/step",JSON.stringify(payload),{operation:"agent_step",request_id,run_id,step:1,collection_ids:[]}),{PUBLIC_KEYS_JSON:publicKeys,DB,AI});
  expect(result.status).toBe(200);expect(await result.json()).toMatchObject({kind:"final",status:"answered",message:"get_imports: 0 observed import jobs"});
});
