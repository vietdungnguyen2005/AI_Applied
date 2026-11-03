import {expect,it} from "vitest";
import worker from "../src/worker";
import {TestDatabase} from "./database";
import {publicKeys,signed} from "./sign";
import {readFileSync} from "node:fs";
export const candidate={profile_id:"supplier-b",version:1,vendor_code:"RIVERBYTE",encoding:"UTF-8",active:true,
  mapping:{sku:"SKU",name:"ProductName",on_hand:"AvailableQuantity"}};
export const mappingBody=(csv="SKU,ProductName,AvailableQuantity\nVM-002,Desk,3\n")=>({input:{raw_base64:Buffer.from(csv).toString("base64"),
  declared_encoding:"UTF-8",selected_vendor_code:"RIVERBYTE",profile_ids:["supplier-b"],method:"rule",synthetic:true},profile_candidates:[candidate]});
it("reuses exact signed profile headers and returns a reviewable draft without changing business data",async()=>{
  const result=await worker.fetch(signed("/ai/mapping/suggest",JSON.stringify(mappingBody()),{operation:"mapping_suggest"}),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase()});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({draft:{status:"suggested",reason:"SIGNED_PROFILE_BASELINE",requires_human_acceptance:true,
    assignments:[{target_field:"sku",source_header:"SKU",basis:"rule"},{target_field:"name",source_header:"ProductName"},{target_field:"on_hand",source_header:"AvailableQuantity"}]},evidence:[]});
});
it("marks invalid quantities and duplicate product identities for row review",async()=>{
  const body=mappingBody("SKU,ProductName,AvailableQuantity\nVM-002,Desk,-3\nVM-002,Desk,4\n");
  const result=await worker.fetch(signed("/ai/mapping/suggest",JSON.stringify(body),{operation:"mapping_suggest"}),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase()});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({draft:{status:"needs_review",warnings:expect.arrayContaining(["ROW_REVIEW_REQUIRED"])}});
});
it("binds the supplier profile to the signed supplier collection",async()=>{
  const result=await worker.fetch(signed("/ai/mapping/suggest",JSON.stringify(mappingBody()),{operation:"mapping_suggest",
    collection_ids:["ed76d914-7c66-5102-9178-676334063938"]}),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase()});
  expect(result.status).toBe(403);
});
it("uses the cloud model to propose distinct supplied headers when the current profile does not match",async()=>{
  const body=mappingBody("ItemRef,DisplayLabel,PhysicalUnits\nVM-002,Desk,3\n");body.input.method="ai";
  const AI={async run(){return {response:JSON.stringify({sku:"ItemRef",name:"DisplayLabel",on_hand:"PhysicalUnits"})};}};
  const result=await worker.fetch(signed("/ai/mapping/suggest",JSON.stringify(body),{operation:"mapping_suggest"}),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase(),AI});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({draft:{status:"needs_review",provider_mode:"live",reason:"MODEL_DRAFT_REQUIRES_REVIEW",
    assignments:[{target_field:"sku",source_header:"ItemRef",basis:"model"},{target_field:"name",source_header:"DisplayLabel"},{target_field:"on_hand",source_header:"PhysicalUnits"}]}});
});
it("preserves Japanese CP932 headers from the original supplier bytes",async()=>{
  const body=mappingBody();
  body.input.raw_base64=readFileSync(new URL("../../data/v1/csv/train/map-a-seeded-01.csv",import.meta.url)).toString("base64");
  body.input.declared_encoding="CP932";body.input.selected_vendor_code="NAMI";body.input.profile_ids=["supplier-a"];
  body.profile_candidates=[{...candidate,profile_id:"supplier-a",encoding:"CP932",vendor_code:"NAMI",mapping:{sku:"商品コード",name:"商品名",on_hand:"在庫数"}}];
  const result=await worker.fetch(signed("/ai/mapping/suggest",JSON.stringify(body),{operation:"mapping_suggest",collection_ids:["ed76d914-7c66-5102-9178-676334063938"]}),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase()});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({draft:{declared_encoding:"CP932",assignments:[{source_header:"商品コード"},{source_header:"商品名"},{source_header:"在庫数"}]}});
});
