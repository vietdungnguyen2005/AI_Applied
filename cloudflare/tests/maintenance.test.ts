import {expect,it} from "vitest";
import worker from "../src/worker";
import {TestDatabase} from "./database";
it("expires old replay keys and budget counters while retaining live records",async()=>{
  const DB=new TestDatabase(),now=Math.floor(Date.now()/1000);
  DB.raw.prepare("INSERT INTO nonces VALUES(?,?,?)").run("cloud","old",now-120);
  DB.raw.prepare("INSERT INTO nonces VALUES(?,?,?)").run("cloud","live",now+120);
  DB.raw.exec("INSERT INTO budgets VALUES('daily:2020-01-01',1)");
  DB.raw.exec("INSERT INTO budgets VALUES('minute:1:actor',1)");
  await (worker as unknown as {scheduled(event:unknown,env:{DB:TestDatabase}):Promise<void>}).scheduled({}, {DB});
  expect(DB.raw.prepare("SELECT nonce FROM nonces").all()).toEqual([{nonce:"live"}]);
  expect(DB.raw.prepare("SELECT * FROM budgets").all()).toEqual([]);
});
it("scrubs expired run payloads and purges retained runs with their audit metadata",async()=>{
  const DB=new TestDatabase(),now=Math.floor(Date.now()/1000),id=crypto.randomUUID();
  const row={id,actor_ref:"a".repeat(64),revision:0,status:"started",phase:"idle",step:0,question:"private question",
    collection_ids:[],history:[],summaries:[],pending:null,outcome:null,reason:null,lease_id:null,lease_until:null,
    expires_at:now-10,purge_after:now+86400,updated_at:now-610};
  DB.raw.prepare("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?)").run(id,row.actor_ref,0,"started",0,row.expires_at,row.purge_after,JSON.stringify(row),crypto.randomUUID(),"start");
  await worker.scheduled({}, {DB});
  const stored=DB.raw.prepare("SELECT payload FROM runs").get() as {payload:string};
  expect(JSON.parse(stored.payload)).toMatchObject({question:"",status:"expired",reason:"TTL_EXPIRED"});
  DB.raw.exec("UPDATE runs SET purge_after=0,revision=revision+1");
  await worker.scheduled({}, {DB});
  expect(DB.raw.prepare("SELECT * FROM runs").all()).toEqual([]);
  expect(DB.raw.prepare("SELECT * FROM run_events").all()).toEqual([]);
});
