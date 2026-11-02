import { z } from "zod";
import { collections, uuid, type Claims, type Database, type GatewayResult, fail } from "./spec";
export const SourceInput = z.strictObject({chunk_id:uuid,collection_ids:collections});
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
