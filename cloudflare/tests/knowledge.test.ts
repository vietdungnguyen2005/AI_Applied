import {expect,it} from "vitest";
import worker from "../src/worker";
import {publicKeys,signed} from "./sign";
import {TestDatabase} from "./database";
it("searches only current chunks in the signed scope and returns bounded lexical hits",async()=>{
  const db=new TestDatabase(),id=crypto.randomUUID();
  db.raw.prepare("INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?,?)").run(id,"4aa83e9f-0a0a-5558-8f5e-0f87db27c923",id,id,"approval","A draft is not approval.","2026-10-01",null,1);
  const request=signed("/ai/knowledge/search",JSON.stringify({query:"draft approval",collection_ids:["4aa83e9f-0a0a-5558-8f5e-0f87db27c923"],top_k:5}),{operation:"knowledge_search"});
  const result=await worker.fetch(request,{PUBLIC_KEYS_JSON:publicKeys,DB:db});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({hits:[{citation:{chunk_id:id},excerpt:"A draft is not approval.",retrieval_mode:"lexical"}]});
});
