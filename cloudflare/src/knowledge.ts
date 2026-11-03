import { z } from "zod";
import { collections, uuid, type Claims, type Database, type GatewayResult, fail } from "./spec";
export const SourceInput = z.strictObject({chunk_id:uuid,collection_ids:collections});
const SearchInput=z.strictObject({query:z.string().min(1).max(2000).refine(q=>Boolean(q.trim())),collection_ids:collections,top_k:z.number().int().min(1).max(5)});
export interface Chunk {chunk_id:string;collection_id:string;document_id:string;version_id:string;
  section:string;text:string;effective_from:string;effective_until:string|null;active:number}
export const citation = (chunk:Chunk) => ({document_id:chunk.document_id,version_id:chunk.version_id,
  chunk_id:chunk.chunk_id,locator:{kind:"section",value:chunk.section},source_url:"/ai/citations/"+chunk.chunk_id});
export interface CitationSpec {execute(body:unknown,claims:Claims):Promise<GatewayResult>}
export class CitationHandler implements CitationSpec {
  constructor(private readonly db:Database){}
  async execute(body:unknown,claims:Claims):Promise<GatewayResult> {
    try {
      const input=SourceInput.safeParse(body);
      if(!input.success) return fail("INPUT_INVALID",400);
      if(input.data.collection_ids.some(id=>!claims.collection_ids.includes(id))) return fail("ACCESS_DENIED",403);
      const scopes=input.data.collection_ids;
      const today=new Date().toISOString().slice(0,10);
      const chunk=await this.db.prepare(`SELECT * FROM chunks WHERE chunk_id=? AND collection_id IN (${scopes.map(()=>"?").join(",")})
        AND active=1 AND effective_from<=? AND (effective_until IS NULL OR effective_until>=?)`)
        .bind(input.data.chunk_id,...scopes,today,today).first<Chunk>();
      if(!chunk)return fail("DOCUMENT_NOT_AVAILABLE",404);
      return {success:true,data:{status:200,body:{request_id:claims.request_id,citation:citation(chunk),
        excerpt:chunk.text.slice(0,2000),truncated:chunk.text.length>2000}}};
    } catch {return fail("DEPENDENCY_UNAVAILABLE",503);}
  }
}
export class KnowledgeHandler implements CitationSpec {
  constructor(private readonly db:Database){}
  async execute(body:unknown,claims:Claims):Promise<GatewayResult>{
    try{
      const parsed=SearchInput.safeParse(body);if(!parsed.success)return fail("INPUT_INVALID",400);
      const input=parsed.data,scopes=input.collection_ids;
      if(scopes.some(id=>!claims.collection_ids.includes(id)))return fail("ACCESS_DENIED",403);
      const today=new Date().toISOString().slice(0,10);
      const {results}=await this.db.prepare(`SELECT * FROM chunks WHERE collection_id IN(${scopes.map(()=>"?").join(",")}) AND active=1
        AND effective_from<=? AND(effective_until IS NULL OR effective_until>=?) ORDER BY chunk_id LIMIT 101`).bind(...scopes,today,today).all<Chunk>();
      if(results.length>100)return fail("INPUT_TOO_LARGE",413);
      const terms=[...new Set(input.query.toLowerCase().match(/[\p{L}\p{N}]+/gu)??[])].slice(0,128);
      const ranked=results.map(chunk=>({chunk,score:terms.filter(t=>(chunk.section+" "+chunk.text).toLowerCase().includes(t)).length}))
        .filter(h=>h.score>0).sort((a,b)=>b.score-a.score||a.chunk.chunk_id.localeCompare(b.chunk.chunk_id)).slice(0,input.top_k);
      return {success:true,data:{status:200,body:{hits:ranked.map(({chunk,score})=>({citation:citation(chunk),excerpt:chunk.text.slice(0,2000),score,retrieval_mode:"lexical"}))}}};
    }catch{return fail("DEPENDENCY_UNAVAILABLE",503);}
  }
}
