import {z} from "zod";
import {uuid,type Claims,type CloudEnv,type GatewayResult,fail} from "./spec";
import {valid} from "./wire";
import {AgentHandler,knownJobs} from "./agent";
const scopes=z.array(uuid).max(10).refine(a=>new Set(a).size===a.length);
const revision=z.number().int().min(0).max(64);
const Start=z.strictObject({action:z.literal("start"),question:z.string().min(1).max(2000).refine(q=>Boolean(q.trim())),
  conversation_id:uuid,collection_ids:scopes});
export const RunCommand=z.discriminatedUnion("action",[Start,z.strictObject({action:z.literal("inspect")}),
  ...(["plan","claim","cancel","recover"] as const).map(action=>z.strictObject({action:z.literal(action),expected_revision:revision})),
  z.strictObject({action:z.literal("record"),expected_revision:revision,lease_id:uuid,observation:z.record(z.string(),z.unknown())})]);
export interface Observation {call_id:string;tool_name:string;status:string;observed_at:string;truncated:boolean;
  data:Record<string,unknown>|null;error_code:string|null}
export interface Intent {call_id:string;tool_name:string;arguments:Record<string,unknown>}
export interface RunRow {
  id:string;actor_ref:string;conversation_id:string;initial_request_id:string;slot:number;status:string;phase:string;
  revision:number;step:number;question:string;collection_ids:string[];history:Observation[];summaries:Record<string,unknown>[];
  pending:Intent|null;outcome:Record<string,unknown>|null;reason:string|null;lease_id:string|null;lease_until:number|null;
  created_at:number;updated_at:number;expires_at:number;purge_after:number;
}
export function snapshot(row:RunRow):Record<string,unknown>{
  const {id,actor_ref,question,collection_ids,history,summaries,pending,lease_id,lease_until,slot,purge_after,...state}=row;
  return {state:{...state,run_id:id,observations:summaries,
    can_resume:(row.status==="started"&&["idle","ready"].includes(row.phase))||(row.status==="waiting_for_operator"&&row.reason==="OUTCOME_UNKNOWN"),
    can_cancel:["started","waiting_for_operator"].includes(row.status)},collection_ids,pending_intent:pending,lease_id,known_job_ids:knownJobs(question,history)};
}
export interface RunSpec {execute(body:unknown,claims:Claims):Promise<GatewayResult>}
export class RunHandler implements RunSpec {
  constructor(private readonly env:CloudEnv){}
  async execute(body:unknown,claims:Claims):Promise<GatewayResult>{
    try{
      const command=RunCommand.safeParse(body);
      if(!command.success)return fail("INPUT_INVALID",400);
      if(!this.env.DB)return fail("CONFIGURATION_UNAVAILABLE",503);
      if(command.data.action!=="start"){
        const stored=await this.env.DB.prepare("SELECT payload FROM runs WHERE id=? AND actor_ref=?")
          .bind(claims.run_id,claims.actor_ref).first<{payload:string}>();
        if(!stored)return fail("RUN_NOT_AVAILABLE",404);
        let row=JSON.parse(stored.payload) as RunRow;
        if(row.collection_ids.some(id=>!claims.collection_ids.includes(id)))return fail("ACCESS_DENIED",403);
        if(row.expires_at<=Math.floor(Date.now()/1000)&&row.status!=="expired"){
          const saved=await this.save(row,{status:"expired",phase:"terminal",question:"",history:[],summaries:[],pending:null,
            outcome:null,reason:"TTL_EXPIRED",lease_id:null,lease_until:null},"expire",claims);
          if(!saved)return fail("STEP_CONFLICT",409);row=saved;
        }
        if(row.status==="started"&&row.lease_until!==null&&row.lease_until<=Math.floor(Date.now()/1000)){
          const saved=await this.save(row,{status:"waiting_for_operator",reason:"OUTCOME_UNKNOWN",lease_id:null,lease_until:null},"interrupted",claims);
          if(!saved)return fail("STEP_CONFLICT",409);row=saved;
        }
        if(command.data.action==="inspect")return this.reply(row);
        if(command.data.expected_revision!==row.revision||claims.step!==row.step||!["started","waiting_for_operator"].includes(row.status))return fail("STEP_CONFLICT",409);
        if(row.revision>=24&&command.data.action!=="cancel"){
          await this.save(row,{status:"failed",phase:"terminal",pending:null,lease_id:null,lease_until:null,reason:"BUDGET_EXCEEDED"},"failed",claims);
          return fail("BUDGET_EXCEEDED",429);
        }
        if(command.data.action==="cancel"){
          const saved=await this.save(row,{status:"cancelled",phase:"terminal",pending:null,lease_id:null,lease_until:null,reason:"OPERATOR_CANCELLED"},"cancel",claims);
          return saved?this.reply(saved):fail("STEP_CONFLICT",409);
        }
        if(command.data.action==="recover"){
          if(row.status!=="waiting_for_operator"||row.reason!=="OUTCOME_UNKNOWN")return fail("STEP_CONFLICT",409);
          const fields:Partial<RunRow>={status:"started",phase:"idle",reason:null,pending:null,lease_id:null,lease_until:null};
          if(row.phase==="executing"){
            if(!row.pending||row.step>=3)return fail("STEP_CONFLICT",409);
            const unknown:Observation={call_id:row.pending.call_id,tool_name:row.pending.tool_name,status:"unavailable",
              observed_at:new Date().toISOString(),truncated:false,data:null,error_code:"UPSTREAM_UNAVAILABLE"};
            Object.assign(fields,{step:row.step+1,history:[...row.history,unknown],summaries:[...row.summaries,summarize(unknown)]});
          }
          const saved=await this.save(row,fields,"operator_resumed",claims);return saved?this.reply(saved):fail("STEP_CONFLICT",409);
        }
        if(command.data.action==="claim"){
          if(row.status!=="started"||row.phase!=="ready"||!row.pending||Date.parse(claims.deadline_at)<=Date.now())return fail("STEP_CONFLICT",409);
          const saved=await this.save(row,{phase:"executing",lease_id:crypto.randomUUID(),
            lease_until:Math.min(Math.ceil(Date.parse(claims.deadline_at)/1000),Math.floor(Date.now()/1000)+30)},"read_claimed",claims);
          return saved?this.reply(saved):fail("STEP_CONFLICT",409);
        }
        if(command.data.action==="record"){
          const input=command.data;
          if(!("observation" in input)||!("lease_id" in input))return fail("INPUT_INVALID",400);
          if(row.status!=="started"||row.phase!=="executing"||row.lease_id!==input.lease_id||!row.lease_until||
            row.lease_until<=Math.floor(Date.now()/1000)||!row.pending)return fail("STEP_CONFLICT",409);
          if(!valid("ToolResult",input.observation))return fail("INPUT_INVALID",400);
          if(new TextEncoder().encode(JSON.stringify(input.observation)).length>16384)return fail("INPUT_TOO_LARGE",413);
          const observed=input.observation as unknown as Observation;
          if(observed.call_id!==row.pending.call_id||observed.tool_name!==row.pending.tool_name)return fail("STEP_CONFLICT",409);
          const summary=summarize(observed);
          const safe=observed.tool_name==="search_supplier_knowledge"&&observed.status==="ok"?{...observed,data:{hits:[]}}:observed;
          const saved=await this.save(row,{phase:"idle",step:row.step+1,history:[...row.history,safe],summaries:[...row.summaries,summary],
            pending:null,lease_id:null,lease_until:null},"read_recorded",claims);
          return saved?this.reply(saved):fail("STEP_CONFLICT",409);
        }
        if(command.data.action==="plan"){
          if(row.phase!=="idle"||row.status!=="started")return fail("STEP_CONFLICT",409);
          const lease=crypto.randomUUID(),until=Math.min(Math.ceil(Date.parse(claims.deadline_at)/1000),Math.floor(Date.now()/1000)+30);
          const planning=await this.save(row,{phase:"planning",lease_id:lease,lease_until:until},"planning",claims);
          if(!planning)return fail("STEP_CONFLICT",409);
          const history=planning.history;
          const response=await new AgentHandler(this.env).execute({protocol_version:1,request_id:claims.request_id,run_id:row.id,
            step:row.step,question:row.question,collection_ids:row.collection_ids,previous_results:history.slice(0,-1),
            tool_result:history.at(-1)??null},claims);
          if(!response.success){await this.save(planning,{status:"failed",phase:"terminal",lease_id:null,lease_until:null,reason:response.error.code},"failed",claims);return response;}
          const final=response.data.body;
          if(planning.lease_until!<=Math.floor(Date.now()/1000))return fail("STEP_CONFLICT",409);
          if(final.kind==="tool_intent"){
            const intent=final.intent as Intent;
            if(row.step>=3||history.some(h=>h.call_id===intent.call_id))return fail("STEP_CONFLICT",409);
            const saved=await this.save(planning,{phase:"ready",pending:intent,lease_id:null,lease_until:null},"planned",claims);
            return saved?this.reply(saved):fail("STEP_CONFLICT",409);
          }
          const handoff=final.kind==="handoff";
          const saved=await this.save(planning,{status:handoff?"waiting_for_operator":"completed",phase:"terminal",pending:null,
            lease_id:null,lease_until:null,reason:handoff?"BUSINESS_HANDOFF":null,
            outcome:{kind:final.kind,status:final.status,handoff_reason:final.handoff_reason}},"planned",claims);
          return saved?this.reply(saved):fail("STEP_CONFLICT",409);
        }
        return fail("STEP_CONFLICT",409);
      }
      const input=Start.parse(command.data),now=Math.floor(Date.now()/1000);
      if(claims.step!==0)return fail("INPUT_INVALID",400);
      if(JSON.stringify(input.collection_ids)!==JSON.stringify(claims.collection_ids))return fail("ACCESS_DENIED",403);
      if(await this.env.DB.prepare("SELECT id FROM runs WHERE id=?").bind(claims.run_id).first())return fail("STEP_CONFLICT",409);
      const old=await this.env.DB.prepare("SELECT payload FROM runs WHERE actor_ref=? AND expires_at<=? AND status IN('started','waiting_for_operator') LIMIT 8")
        .bind(claims.actor_ref,now).all<{payload:string}>();
      for(const stored of old.results){await this.save(JSON.parse(stored.payload) as RunRow,{status:"expired",phase:"terminal",question:"",history:[],summaries:[],
        pending:null,outcome:null,reason:"TTL_EXPIRED",lease_id:null,lease_until:null},"expire",claims);}
      for(let slot=0;slot<8;slot++){
        const row:RunRow={id:claims.run_id,actor_ref:claims.actor_ref,conversation_id:input.conversation_id,
          initial_request_id:claims.request_id,slot,status:"started",phase:"idle",revision:0,step:0,question:input.question,
          collection_ids:input.collection_ids,history:[],summaries:[],pending:null,outcome:null,reason:null,lease_id:null,lease_until:null,
          created_at:now,updated_at:now,expires_at:now+600,purge_after:now+600+86400};
        const inserted=await this.env.DB.prepare(`INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING RETURNING id`)
          .bind(row.id,row.actor_ref,0,row.status,slot,row.expires_at,row.purge_after,JSON.stringify(row),claims.request_id,"start").first();
        if(inserted)return this.reply(row);
      }
      return fail("BUDGET_EXCEEDED",429);
    }catch{return fail("DEPENDENCY_UNAVAILABLE",503);}
  }
  private reply(row:RunRow):GatewayResult{
    const output=snapshot(row);return valid("RunSnapshot",output)?{success:true,data:{status:200,body:output}}:fail("OUTPUT_INVALID",502);
  }
  private async save(old:RunRow,fields:Partial<RunRow>,kind:string,claims:Claims):Promise<RunRow|null>{
    const row={...old,...fields,revision:old.revision+1,updated_at:Math.floor(Date.now()/1000)};
    const saved=await this.env.DB!.prepare(`UPDATE runs SET revision=?,status=?,payload=?,request_id=?,event_kind=? WHERE id=? AND actor_ref=? AND revision=? RETURNING id`)
      .bind(row.revision,row.status,JSON.stringify(row),claims.request_id,kind,row.id,row.actor_ref,old.revision).first();
    return saved?row:null;
  }
}
export function summarize(observed:Observation):Record<string,unknown>{
  let count=0;
  if(observed.data){const array=["profiles","imports","hits"].map(k=>observed.data![k]).find(Array.isArray);count=array?array.length:1;}
  const {call_id,tool_name,status,observed_at,truncated,error_code}=observed;
  return {call_id,tool_name,status,observed_at,truncated,error_code,item_count:count};
}
