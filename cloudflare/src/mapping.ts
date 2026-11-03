import {parse} from "csv-parse/browser/esm/sync";
import {Buffer} from "node:buffer";
import {hash} from "./authentication";
import {type Claims,type CloudEnv,type GatewayResult,fail} from "./spec";
import {valid} from "./wire";
import {ModelHandler} from "./model";
import {z} from "zod";
import {strictJson} from "./json";
import {profileColumns} from "./column-profile";
import {PROMPT_VERSION,TARGET_SCHEMA,EXAMPLES,MAPPING_SYSTEM} from "./mapping-context";
import {semanticCandidates} from "./semantic-candidates";
type Target="sku"|"name"|"on_hand";
const targets:Target[]=["sku","name","on_hand"];
const comparable=(header:string)=>header.normalize("NFKC").toLowerCase().replace(/[\s_.-]/gu,"");
interface Candidate {profile_id:string;version:number;vendor_code:string;encoding:"UTF-8"|"CP932";active:boolean;mapping:Record<Target,string>}
interface MappingInput {input:{raw_base64:string;declared_encoding:"UTF-8"|"CP932";selected_vendor_code:string;profile_ids:string[];method:"ai"|"rule";synthetic:true};profile_candidates:Candidate[]}
export interface MappingSpec {execute(body:unknown,claims:Claims):Promise<GatewayResult>}
export class MappingHandler implements MappingSpec {
  constructor(private readonly env:CloudEnv){}
  async execute(body:unknown,claims:Claims):Promise<GatewayResult>{
    try{
      if(!valid("IntegratedMappingRequest",body))return fail("INPUT_INVALID",400);
      const {input,profile_candidates:[profile]}=body as MappingInput;
      const scopes:Record<string,string>={NAMI:"ed76d914-7c66-5102-9178-676334063938",RIVERBYTE:"4aa83e9f-0a0a-5558-8f5e-0f87db27c923"};
      if(!scopes[profile.vendor_code]||!claims.collection_ids.includes(scopes[profile.vendor_code]))return fail("ACCESS_DENIED",403);
      if(!profile.active||profile.version<1||!/^[a-z][a-z0-9-]{0,47}$/.test(profile.profile_id)||profile.vendor_code!==input.selected_vendor_code||
        profile.encoding!==input.declared_encoding||JSON.stringify(input.profile_ids)!==JSON.stringify([profile.profile_id])||
        Object.keys(profile.mapping).length!==3||new Set(Object.values(profile.mapping)).size!==3)return fail("INPUT_INVALID",400);
      const raw=Buffer.from(input.raw_base64,"base64");
      if(raw.toString("base64")!==input.raw_base64||raw.length===0)return fail("INPUT_INVALID",400);
      if(raw.length>45000)return fail("INPUT_TOO_LARGE",413);
      let text:string,records:string[][];
      try{
        text=new TextDecoder(input.declared_encoding==="UTF-8"?"utf-8":"shift_jis",{fatal:true,ignoreBOM:true}).decode(raw);
        records=parse(text,{bom:false,skip_empty_lines:false,relax_column_count:false,max_record_size:45000});
      }catch{return fail("INPUT_INVALID",400);}
      const headers=records[0],rows=records.slice(1);
      if(!headers?.length||headers.length>100||rows.length<1||rows.length>1000||headers.some(h=>!h||h!==h.trim()||h.length>80||/[\u0000-\u001f\u007f-\u009f\ufeff]/u.test(h))||
        new Set(headers.map(h=>h.normalize("NFKC").toLowerCase())).size!==headers.length)return fail("INPUT_INVALID",400);
      let mapping:Partial<Record<Target,string>>={};
      const ambiguous=new Set<Target>();
      for(const target of targets){
        const matches=headers.filter(h=>comparable(h)===comparable(profile.mapping[target]));
        if(matches.length===1)mapping[target]=matches[0];
        if(matches.length>1)ambiguous.add(target);
      }
      if(new Set(Object.values(mapping)).size!==Object.keys(mapping).length)return fail("INPUT_INVALID",400);
      const profileLocked={...mapping};
      const columns=profileColumns(headers,rows);
      const inferred=input.method==="ai"?semanticCandidates(columns,profileLocked):{};
      for(const target of targets)if(inferred[target]&&!ambiguous.has(target))mapping[target]=inferred[target];
      const locked={...mapping},hasInferred=targets.some(t=>Boolean(inferred[t])&&!ambiguous.has(t));
      const warnings=["FRESHNESS_UNVERIFIED","ENCODING_DECLARED","BUSINESS_VALIDATION_REQUIRED","SOURCE_UNTRUSTED","RULE_BASELINE"];
      if(ambiguous.size)warnings.push("AMBIGUOUS_HEADER");
      let model=false;
      if(targets.some(t=>!locked[t]&&!ambiguous.has(t))&&headers.some(h=>!Object.values(locked).includes(h))&&input.method==="ai"){
        if(columns.some(c=>c.examples_truncated)||rows.length>50)warnings.push("SAMPLE_TRUNCATED");
        const choice={anyOf:[{type:"string",enum:headers.filter(h=>!Object.values(locked).includes(h))},{type:"null"}]};
        const result=await new ModelHandler(this.env).execute(MAPPING_SYSTEM,
          JSON.stringify({prompt_version:PROMPT_VERSION,target_schema:TARGET_SCHEMA,examples:EXAMPLES,headers,columns,
            supplier_context:{vendor_code:profile.vendor_code,profile_id:profile.profile_id,version:profile.version},
            locked_mapping:locked,blocked_targets:[...ambiguous],requested_targets:targets.filter(t=>!locked[t]&&!ambiguous.has(t))}),{type:"object",additionalProperties:false,
            properties:Object.fromEntries(targets.map(t=>[t,locked[t]?{type:"string",const:locked[t]}:ambiguous.has(t)?{type:"null"}:choice])),required:targets},claims);
        if(!result.success)return result;
        let proposed;
        try{proposed=z.strictObject({sku:z.string().nullable(),name:z.string().nullable(),on_hand:z.string().nullable()})
          .parse(strictJson(result.data.body.text as string));}catch{return fail("OUTPUT_INVALID",502);}
        if(targets.some(t=>locked[t]&&proposed[t]!==locked[t]))return fail("OUTPUT_INVALID",502);
        if(targets.some(t=>ambiguous.has(t)&&proposed[t]!==null))return fail("OUTPUT_INVALID",502);
        mapping=Object.fromEntries(targets.filter(t=>proposed[t]!==null).map(t=>[t,proposed[t]!])) as Partial<Record<Target,string>>;
        if(Object.values(mapping).some(h=>!headers.includes(h))||new Set(Object.values(mapping)).size!==Object.keys(mapping).length)return fail("OUTPUT_INVALID",502);
        // A profile-approved product key wins; an unapproved bare supplier/vendor ID is not a SKU.
        if(!locked.sku&&mapping.sku&&/supplier|vendor|仕入先|取引先|供給者/iu.test(mapping.sku)&&
          !/product|item|sku|商品|品目/iu.test(mapping.sku)){
          delete mapping.sku;warnings.push("MODEL_OUTPUT_INVALID");
        }
        model=true;warnings.splice(warnings.indexOf("RULE_BASELINE"),1);warnings.push("NO_AUTHORIZED_SOP");
      }
      const assignments=targets.filter(t=>mapping[t]).map(t=>({target_field:t,source_header:mapping[t]!,basis:model&&!locked[t]?"model":"rule",uncertainty:!profileLocked[t]?"high":"medium",
        reason:inferred[t]?"Unique target meaning and sampled type support this column; human review required.":model&&!locked[t]?"Model inferred header semantics; human review required.":mapping[t]===profile.mapping[t]?
          "Exact header from current signed Java profile; human review required.":"Unambiguous formatting match to signed profile; original source header retained; human review required.",citations:[]}));
      const seen=new Set<string>();
      const review=rows.some(row=>{
        const value=(target:Target)=>mapping[target]?row[headers.indexOf(mapping[target]!)].trim():null;
        const sku=value("sku")?.toUpperCase(),name=value("name"),qty=value("on_hand");
        if(sku!==null&&sku!==undefined){if(!sku||[...sku].length>64||seen.has(sku))return true;seen.add(sku);}
        return name!==null&&(!name||[...name].length>160)||qty!==null&&(!/^[0-9]{1,7}$/.test(qty)||Number(qty)>1000000);
      });
      if(review)warnings.push("ROW_REVIEW_REQUIRED");
      if(headers.some(h=>!Object.values(mapping).includes(h)))warnings.push("UNMAPPED_HEADER");
      const draft={request_id:claims.request_id,raw_sha256:await hash(new Uint8Array(raw)),declared_encoding:input.declared_encoding,
        selected_vendor_code:input.selected_vendor_code,vendor_code:profile.vendor_code,vendor_verification:"bff_profile_snapshot",
        status:assignments.length?(assignments.length===3&&!review&&!model&&!hasInferred?"suggested":"needs_review"):"abstained",assignments,unmapped_headers:headers.filter(h=>!Object.values(mapping).includes(h)),
        missing_required_fields:targets.filter(t=>!mapping[t]),warnings,reason:model?"MODEL_DRAFT_REQUIRES_REVIEW":hasInferred?"SEMANTIC_COLUMN_RULE_DRAFT":assignments.length===3?"SIGNED_PROFILE_BASELINE":assignments.length?"PARTIAL_SIGNED_PROFILE_BASELINE":"UNMAPPED_HEADER",
        profile_differences:[{profile_id:profile.profile_id,version:profile.version,active:true,encoding_matches:true,
          changes:Object.fromEntries(targets.filter(t=>profile.mapping[t]!==mapping[t]).map(t=>[t,[profile.mapping[t],mapping[t]??null]]))}],
        requires_human_acceptance:true,provider_mode:"live"};
      const output={draft,evidence:[]};
      return valid("IntegratedMappingResponse",output)?{success:true,data:{status:200,body:output}}:fail("OUTPUT_INVALID",502);
    }catch{return fail("DEPENDENCY_UNAVAILABLE",503);}
  }
}
