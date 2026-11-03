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
it("preserves independently matched profile columns when one source header changes",async()=>{
  const body=mappingBody("SKU,ProductName,PhysicalUnits\nVM-002,Desk,3\n");
  const result=await worker.fetch(signed("/ai/mapping/suggest",JSON.stringify(body),{operation:"mapping_suggest"}),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase()});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({draft:{status:"needs_review",reason:"PARTIAL_SIGNED_PROFILE_BASELINE",
    missing_required_fields:["on_hand"],assignments:[{target_field:"sku",source_header:"SKU",basis:"rule"},{target_field:"name",source_header:"ProductName",basis:"rule"}]}});
});
it("asks the model only for missing columns and keeps signed assignments rule-based",async()=>{
  const body=mappingBody("SKU,ProductName,PhysicalUnits\nVM-002,Desk,3\n");body.input.method="ai";
  let calls=0;
  const AI={async run(_model:string,input:Record<string,unknown>){calls++;
    const payload=JSON.parse((input.messages as {content:string}[])[1].content);
    expect(payload.locked_mapping).toEqual({sku:"SKU",name:"ProductName"});
    return {response:JSON.stringify({sku:"SKU",name:"ProductName",on_hand:"PhysicalUnits"})};}};
  const result=await worker.fetch(signed("/ai/mapping/suggest",JSON.stringify(body),{operation:"mapping_suggest"}),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase(),AI});
  expect(result.status).toBe(200);expect(calls).toBe(1);
  expect(await result.json()).toMatchObject({draft:{assignments:[{target_field:"sku",basis:"rule"},{target_field:"name",basis:"rule"},{target_field:"on_hand",basis:"model"}]}});
});
it("rejects a model that changes a locked profile assignment despite the decoding schema",async()=>{
  const body=mappingBody("SKU,ProductName,PhysicalUnits,OtherCode\nVM-002,Desk,3,OTHER\n");body.input.method="ai";
  const AI={async run(){return {response:JSON.stringify({sku:"OtherCode",name:"ProductName",on_hand:"PhysicalUnits"})};}};
  const result=await worker.fetch(signed("/ai/mapping/suggest",JSON.stringify(body),{operation:"mapping_suggest"}),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase(),AI});
  expect(result.status).toBe(502);
});
it("matches harmless profile formatting changes without altering original source headers",async()=>{
  const body=mappingBody("sku,Product_Name,Available Quantity\nVM-002,Desk,3\n");
  const result=await worker.fetch(signed("/ai/mapping/suggest",JSON.stringify(body),{operation:"mapping_suggest"}),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase()});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({draft:{assignments:[{source_header:"sku",basis:"rule"},{source_header:"Product_Name",basis:"rule"},{source_header:"Available Quantity",basis:"rule"}]}});
});
it("does not silently lock a normalized match when two source headers collide",async()=>{
  const body=mappingBody("SKU,ProductName,AvailableQuantity,Available_Quantity\nVM-002,Desk,3,4\n");
  const result=await worker.fetch(signed("/ai/mapping/suggest",JSON.stringify(body),{operation:"mapping_suggest"}),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase()});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({draft:{missing_required_fields:["on_hand"],warnings:expect.arrayContaining(["AMBIGUOUS_HEADER"])}});
});
it("sends bounded representative column profiles including late rows rather than two initial blanks",async()=>{
  const rows=Array.from({length:100},(_,i)=>i<2?",,":`VM-${i},Product ${i},${i}`);
  const body=mappingBody("ItemKey,DisplayText,PhysicalUnits\n"+rows.join("\n")+"\n");body.input.method="ai";
  let captured:Record<string,unknown>={};
  const AI={async run(_model:string,input:Record<string,unknown>){captured=JSON.parse((input.messages as {content:string}[])[1].content);
    return {response:JSON.stringify({sku:"ItemKey",name:"DisplayText",on_hand:"PhysicalUnits"})};}};
  const result=await worker.fetch(signed("/ai/mapping/suggest",JSON.stringify(body),{operation:"mapping_suggest"}),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase(),AI});
  expect(result.status).toBe(200);
  expect(captured.columns).toEqual(expect.arrayContaining([expect.objectContaining({header:"ItemKey",sample_count:50,non_empty_count:49,
    examples:expect.arrayContaining(["VM-99"])}),expect.objectContaining({header:"PhysicalUnits",integer_ratio:1,quantity_ratio:1})]));
  expect(captured.sample_rows).toBeUndefined();
});
it("provides explicit target semantics, an immutable prompt version and two examples to the model",async()=>{
  const body=mappingBody("ItemKey,DisplayText,PhysicalUnits\nVM-002,Desk,3\n");body.input.method="ai";
  let captured:Record<string,unknown>={},system="";
  const AI={async run(_model:string,input:Record<string,unknown>){const messages=input.messages as {content:string}[];
    system=messages[0].content;captured=JSON.parse(messages[1].content);
    return {response:JSON.stringify({sku:"ItemKey",name:"DisplayText",on_hand:"PhysicalUnits"})};}};
  expect((await worker.fetch(signed("/ai/mapping/suggest",JSON.stringify(body),{operation:"mapping_suggest"}),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase(),AI})).status).toBe(200);
  expect(captured.prompt_version).toBe("mapping-context-v3");
  expect(captured.target_schema).toMatchObject({on_hand:{description:expect.stringContaining("physical")}});
  expect(captured.examples).toHaveLength(2);
  expect(system).toContain("locked_mapping");expect(system).toContain("not probabilities");
});
it("returns the partial profile without calling a model when no unused source columns remain",async()=>{
  const body=mappingBody("SKU,ProductName\nVM-002,Desk\n");body.input.method="ai";
  let calls=0;const AI={async run(){calls++;return {response:'{"sku":"SKU","name":"ProductName","on_hand":null}'};}};
  const result=await worker.fetch(signed("/ai/mapping/suggest",JSON.stringify(body),{operation:"mapping_suggest"}),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase(),AI});
  expect(result.status).toBe(200);expect(calls).toBe(0);
  expect(await result.json()).toMatchObject({draft:{missing_required_fields:["on_hand"],assignments:[{basis:"rule"},{basis:"rule"}]}});
});
it("omits absent historical column bindings from model evidence while retaining current locks",async()=>{
  const body=mappingBody("SKU,ProductName,PhysicalUnits\nVM-002,Desk,3\n");body.input.method="ai";
  let captured:Record<string,unknown>={};
  const AI={async run(_model:string,input:Record<string,unknown>){captured=JSON.parse((input.messages as {content:string}[])[1].content);
    return {response:'{"sku":"SKU","name":"ProductName","on_hand":"PhysicalUnits"}'};}};
  expect((await worker.fetch(signed("/ai/mapping/suggest",JSON.stringify(body),{operation:"mapping_suggest"}),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase(),AI})).status).toBe(200);
  expect(captured.profile_candidate).toBeUndefined();
  expect(captured.supplier_context).toEqual({vendor_code:"RIVERBYTE",profile_id:"supplier-b",version:1});
});
it("keeps supported fields when a model confuses supplier identity with product identity",async()=>{
  const body=mappingBody("VendorReference,ProductName,PhysicalUnits\nRIVERBYTE,Desk,3\nRIVERBYTE,Bag,4\n");body.input.method="ai";
  const AI={async run(){return {response:'{"sku":"VendorReference","name":"ProductName","on_hand":"PhysicalUnits"}'};}};
  const result=await worker.fetch(signed("/ai/mapping/suggest",JSON.stringify(body),{operation:"mapping_suggest"}),{PUBLIC_KEYS_JSON:publicKeys,DB:new TestDatabase(),AI});
  expect(result.status).toBe(200);
  expect(await result.json()).toMatchObject({draft:{missing_required_fields:["sku"],assignments:[{target_field:"name"},{target_field:"on_hand"}]}});
});
