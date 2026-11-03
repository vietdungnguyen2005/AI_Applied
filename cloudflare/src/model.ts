import {z} from "zod";
import {type Claims,type CloudEnv,type GatewayResult,fail} from "./spec";
export const MODEL="@cf/qwen/qwen3-30b-a3b-fp8";
export interface ModelSpec {execute(system:string,payload:string,schema:Record<string,unknown>,claims:Claims):Promise<GatewayResult>}
export class ModelHandler implements ModelSpec {
  constructor(private readonly env:CloudEnv){}
  async execute(system:string,payload:string,schema:Record<string,unknown>,claims:Claims):Promise<GatewayResult>{
    let timer:ReturnType<typeof setTimeout>|undefined;
    try{
      if(!this.env.DB||!this.env.AI)return fail("CONFIGURATION_UNAVAILABLE",503);
      if(payload.length>8000)return fail("INPUT_TOO_LARGE",413);
      const deadline=Math.min(Date.parse(claims.deadline_at),Date.now()+12000);
      if(deadline<=Date.now())return fail("DEADLINE_EXCEEDED",504);
      const reserve=async(bucket:string,limit:number)=>this.env.DB!.prepare(`INSERT INTO budgets(bucket,used) VALUES(?,1)
        ON CONFLICT(bucket) DO UPDATE SET used=used+1 WHERE used<? RETURNING used`).bind(bucket,limit).first();
      if(!await reserve("minute:"+Math.floor(Date.now()/60000)+":"+claims.actor_ref,4))return fail("BUDGET_EXCEEDED",429);
      if(!await reserve("daily:"+new Date().toISOString().slice(0,10),60))return fail("BUDGET_EXCEEDED",429);
      if(deadline<=Date.now())return fail("DEADLINE_EXCEEDED",504);
      const inference=this.env.AI.run(MODEL,{messages:[{role:"system",content:system},{role:"user",content:payload}],
        max_tokens:512,temperature:0,response_format:{type:"json_schema",json_schema:schema}});
      const raw=await Promise.race([inference,new Promise<null>(resolve=>{timer=setTimeout(()=>resolve(null),deadline-Date.now());})]);
      if(raw===null)return fail("DEADLINE_EXCEEDED",504);
      const response=z.object({response:z.string().max(16000)}).safeParse(raw);
      const chat=z.object({choices:z.array(z.object({message:z.object({content:z.string().max(16000)})})).min(1)}).safeParse(raw);
      const text=response.success?response.data.response:chat.success?chat.data.choices[0].message.content:null;
      return text===null?fail("OUTPUT_INVALID",502):{success:true,data:{status:200,body:{text}}};
    }catch{return fail("DEPENDENCY_UNAVAILABLE",503);}
    finally{if(timer!==undefined)clearTimeout(timer);}
  }
}
