import { describe, expect, it } from "vitest";
import worker from "../src/worker";
import { publicKeys, signed } from "./sign";
import { TestDatabase } from "./database";

describe("public cloud boundary", () => {
  it("does not report ready when the inference binding is missing", async()=>{
    const result=await worker.fetch(new Request("https://ai.example/ready"),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase()});
    expect(result.status).toBe(503);
  });
  it("reads a current citation only inside its signed collection", async () => {
    const db = new TestDatabase();
    db.raw.exec(`CREATE TABLE IF NOT EXISTS chunks(chunk_id TEXT PRIMARY KEY,collection_id TEXT,document_id TEXT,
      version_id TEXT,section TEXT,text TEXT,effective_from TEXT,effective_until TEXT,active INTEGER);`);
    const id = "22222222-2222-2222-2222-222222222222";
    db.raw.prepare("INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?,?)").run(id,"4aa83e9f-0a0a-5558-8f5e-0f87db27c923",id,id,"approval","A draft is not approval.","2026-10-01",null,1);
    const result = await worker.fetch(signed("/ai/citations/read",JSON.stringify({chunk_id:id,
      collection_ids:["4aa83e9f-0a0a-5558-8f5e-0f87db27c923"]}),{operation:"documents_read"}),
      {PUBLIC_KEYS_JSON:publicKeys,DB:db});
    expect(result.status).toBe(200);
    expect(await result.json()).toMatchObject({excerpt:"A draft is not approval.",truncated:false,
      citation:{chunk_id:id,source_url:"/ai/citations/"+id,locator:{kind:"section",value:"approval"}}});
  });
  it("reports readiness unavailable when persistent storage is not configured", async () => {
    const result = await worker.fetch(new Request("https://ai.example/ready"),{});
    expect(result.status).toBe(503);
    expect(await result.json()).toEqual({code:"CONFIGURATION_UNAVAILABLE"});
  });
  it("refuses malformed ask bodies instead of treating them as a provider failure", async () => {
    const result = await worker.fetch(signed("/ai/ask", '{"question":42}'),
      {PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase()});
    expect(result.status).toBe(400);
  });
  it("rejects collections outside the signed grant before inference", async () => {
    const request = signed("/ai/ask", JSON.stringify({question:"What is the policy?",language:"en",
      collection_ids:["11111111-1111-1111-1111-111111111111"]}));
    const result = await worker.fetch(request, {PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase()});
    expect(result.status).toBe(403);
  });
  it("exposes liveness without credentials or model/storage calls", async () => {
    const result = await worker.fetch(new Request("https://ai.example/health"), {});
    expect(result.status).toBe(200);
    expect(await result.json()).toEqual({status: "ok"});
  });
  it("rejects unsigned AI requests before touching storage or inference", async () => {
    const result = await worker.fetch(new Request("https://ai.example/ai/ask", {
      method: "POST", body: "{}", headers: {"Content-Type": "application/json"},
    }), {});
    expect(result.status).toBe(401);
    expect(await result.json()).toEqual({code: "ACCESS_DENIED"});
  });
  it("rejects a body changed after a valid BFF signature", async () => {
    const request = signed("/ai/ask", '{}');
    const changed = new Request(request.url, {method: "POST", headers: request.headers, body: '{"question":"forged"}'});
    const result = await worker.fetch(changed, {PUBLIC_KEYS_JSON: publicKeys});
    expect(result.status).toBe(401);
  });
  it("rejects duplicate JSON keys even when the exact body was signed", async () => {
    const request = signed("/ai/ask", '{"question":"safe","question":"injected"}');
    const result = await worker.fetch(request, {PUBLIC_KEYS_JSON: publicKeys});
    expect(result.status).toBe(400);
  });
  it("atomically refuses reuse of a valid signed nonce even after a service failure", async () => {
    const request = signed("/ai/ask", JSON.stringify({question:"What is the policy?",language:"en",
      collection_ids:["4aa83e9f-0a0a-5558-8f5e-0f87db27c923"]}));
    const env = {PUBLIC_KEYS_JSON: publicKeys, DB: new TestDatabase()};
    env.DB.raw.prepare("INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?,?)").run(
      crypto.randomUUID(),"4aa83e9f-0a0a-5558-8f5e-0f87db27c923",crypto.randomUUID(),crypto.randomUUID(),
      "approval","A draft is not approval.","2026-10-01",null,1);
    const first = await worker.fetch(request.clone(), env);
    expect(first.status).toBe(503);
    const second = await worker.fetch(request.clone(), env);
    expect(second.status).toBe(409);
  });
});
