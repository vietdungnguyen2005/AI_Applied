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
