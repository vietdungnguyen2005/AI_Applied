/** Owner-operated live diagnostic. Signing credentials are environment-only; never write them to artifacts. */
import {createHash,createPrivateKey,randomUUID,sign} from "node:crypto";
import {existsSync,readFileSync,readdirSync,writeFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {resolve,join} from "node:path";
import {spawnSync} from "node:child_process";

const args=Object.fromEntries(process.argv.slice(2).map((value,index,all)=>index%2===0?[value,all[index+1]]:null).filter(Boolean));
const arm=args["--arm"],suite=args["--suite"],origin=new URL(args["--origin"]??"https://invalid.invalid");
const transport=args["--transport"]??"fetch";
if(!["fetch","curl"].includes(transport))throw new Error("Unknown transport");
if(!["baseline","candidate"].includes(arm)||!suite||!/^[a-z0-9-]+$/.test(suite)||origin.protocol!=="https:"||origin.username||origin.password||origin.search||origin.hash||origin.pathname!=="/") {
  throw new Error("Usage: node tools/run-mapping-pilot.mjs --arm baseline|candidate --suite NAME --origin https://WORKER_HOST");
}
const kid=process.env.AI_SIGNING_KID,keyData=process.env.AI_SIGNING_KEY_PKCS8_BASE64;
if(!kid||!keyData)throw new Error("Set BFF signing credentials in the process environment");
const key=createPrivateKey({key:Buffer.from(keyData,"base64"),type:"pkcs8",format:"der"});
if(key.asymmetricKeyType!=="ed25519")throw new Error("Ed25519 key required");
const directory=resolve(fileURLToPath(new URL("../../evals/cloud-mapping/",import.meta.url)),suite);
const bytes=readFileSync(join(directory,"cases.json")),cases=JSON.parse(bytes),freeze=JSON.parse(readFileSync(join(directory,"freeze.json"),"utf8"));
if(createHash("sha256").update(bytes).digest("hex")!==freeze.cases_sha256)throw new Error("Frozen input bytes changed");
const file=join(directory,arm+"-raw.json"),records=existsSync(file)?JSON.parse(readFileSync(file,"utf8")):[];
let latest=0;
for(const entry of readdirSync(resolve(directory,".."),{withFileTypes:true})){
  if(!entry.isDirectory())continue;
  for(const other of ["baseline","candidate"]){
    const path=resolve(directory,"..",entry.name,other+"-raw.json");
    if(existsSync(path))for(const record of JSON.parse(readFileSync(path,"utf8")))latest=Math.max(latest,Date.parse(record.at));
  }
}
const pause=async(ms)=>{if(ms>0){console.log(`Quota pacing: ${ms}ms`);await new Promise(r=>setTimeout(r,ms));}};
await pause(65000-(Date.now()-latest));
let batch=0;
for(const item of cases){
  if(records.some(r=>r.id===item.id))continue; // Includes failures: never retry a recorded observation.
  if(batch===4){await pause(65000);batch=0;}
  const csv=[item.headers,...item.rows].map(row=>row.map(v=>'"'+v.replaceAll('"','""')+'"').join(",")).join("\n")+"\n";
  const payload={input:{raw_base64:Buffer.from(csv).toString("base64"),declared_encoding:"UTF-8",selected_vendor_code:"RIVERBYTE",
    profile_ids:["supplier-b"],method:"ai",synthetic:true},profile_candidates:[{profile_id:"supplier-b",version:1,vendor_code:"RIVERBYTE",
    encoding:"UTF-8",active:true,mapping:{sku:"SKU",name:"ProductName",on_hand:"AvailableQuantity"}}]};
  const body=JSON.stringify(payload),now=Math.floor(Date.now()/1000),id=randomUUID(),path="/ai/mapping/suggest";
  const sha=value=>createHash("sha256").update(value).digest("hex");
  const digest=sha(["vmarket-ai-request:v1","POST",path,"application/json",...Array(7).fill(""),sha(body),""].join("\n"));
  const claims={version:1,issuer:"vmarket-bff",audience:"vmarket-ai",mode:"integrated",kid,actor_ref:sha("mapping-pilot-v1"),
    request_id:id,run_id:randomUUID(),step:0,collection_ids:["4aa83e9f-0a0a-5558-8f5e-0f87db27c923"],
    deadline_at:new Date((now+25)*1000).toISOString(),issued_at:now,expires_at:now+25,nonce:randomUUID(),operation:"mapping_suggest",request_digest:digest};
  const context=Buffer.from(JSON.stringify(claims)).toString("base64url"),start=Date.now();let record;
  try{
    const headers={
      "Content-Type":"application/json","X-Request-ID":id,"X-AI-Context":context,
      "X-AI-Signature":sign(null,Buffer.from("vmarket-ai-context:v1."+context),key).toString("base64url")};
    let status,responseBody;
    if(transport==="curl"){
      // Credentials travel over stdin, never process arguments, shell interpolation or disk.
      const quoted=value=>'"'+value.replaceAll('\\','\\\\').replaceAll('"','\\"').replaceAll('\n','\\n').replaceAll('\r','\\r')+'"';
      const config=["silent","show-error","max-time = 26","request = POST","url = "+quoted(new URL(path,origin).href),
        ...Object.entries(headers).map(([name,value])=>"header = "+quoted(name+": "+value)),"data = "+quoted(body),'write-out = "\\n%{http_code}"'].join("\n");
      const result=spawnSync("curl",["--config","-"],{input:config,encoding:"utf8",timeout:28000,maxBuffer:1000000,windowsHide:true});
      if(result.error||result.status!==0)throw new Error("CurlTransportFailure");
      const offset=result.stdout.lastIndexOf("\n");status=Number(result.stdout.slice(offset+1));responseBody=JSON.parse(result.stdout.slice(0,offset));
    }else{
      const response=await fetch(new URL(path,origin),{method:"POST",body,redirect:"error",signal:AbortSignal.timeout(26000),headers});
      status=response.status;responseBody=await response.json();
    }
    record={id:item.id,arm,status,ms:Date.now()-start,at:new Date().toISOString(),transport,response:responseBody};
  }catch(error){record={id:item.id,arm,status:0,ms:Date.now()-start,at:new Date().toISOString(),transport,error:error.name};}
  records.push(record);writeFileSync(file,JSON.stringify(records,null,2)+"\n");batch++;
  console.log(JSON.stringify({id:item.id,status:record.status,ms:record.ms}));
  if(record.status!==200)throw new Error("Non-success observation preserved; no automatic retry");
}
