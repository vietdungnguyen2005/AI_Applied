import { Context, type AuthResult, type AuthenticationSpec } from "./spec";
import { strictJson } from "./json";

const operations: Record<string, string> = {"/ai/ask": "ask", "/ai/citations/read": "documents_read",
  "/ai/knowledge/search": "knowledge_search", "/ai/agent/step": "agent_step",
  "/ai/runs/control": "run_control", "/ai/mapping/suggest": "mapping_suggest"};
export async function hash(bytes: Uint8Array<ArrayBuffer>): Promise<string> {
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), b => b.toString(16).padStart(2,"0")).join("");
}
function decode(value: string): Uint8Array<ArrayBuffer> {
  if (!/^[A-Za-z0-9_-]+$/.test(value)) throw new Error("encoding");
  const bytes = Uint8Array.from(atob(value.replace(/-/g,"+").replace(/_/g,"/") + "=".repeat((4-value.length%4)%4)), c => c.charCodeAt(0));
  if (btoa(String.fromCharCode(...bytes)).replace(/=/g,"").replace(/\+/g,"-").replace(/\//g,"_") !== value) throw new Error("encoding");
  return bytes;
}

export class AuthenticationHandler implements AuthenticationSpec {
  constructor(private readonly publicKeys: string | undefined) {}
  async execute(request: Request): Promise<AuthResult> {
    try {
      const url = new URL(request.url);
      const encoded = request.headers.get("X-AI-Context") ?? "";
      const signature = request.headers.get("X-AI-Signature") ?? "";
      if (request.method !== "POST" || !operations[url.pathname] || url.search || url.hash ||
          encoded.length < 1 || encoded.length > 4096 || signature.length !== 86 ||
          request.headers.get("Content-Type") !== "application/json") return {success:false,error:{code:"ACCESS_DENIED",status:401,recoverable:false}};
      for (const [name] of request.headers) {
        if (["cookie","authorization","x-csrf-token","x-v-market-bff-secret","x-v-market-ops-secret","x-vendor-code"].includes(name.toLowerCase()) ||
            name.toLowerCase().startsWith("x-source-") || name.toLowerCase().startsWith("x-doc-")) {
          return {success:false,error:{code:"ACCESS_DENIED",status:401,recoverable:false}};
        }
      }
      const claims = Context.parse(strictJson(new TextDecoder("utf-8",{fatal:true}).decode(decode(encoded))));
      const keys: Record<string,string> = JSON.parse(this.publicKeys ?? "{}");
      const rawKey = Uint8Array.from(atob(keys[claims.kid]), c=>c.charCodeAt(0));
      if (rawKey.length !== 32) throw new Error("key");
      const key = await crypto.subtle.importKey("raw", rawKey, {name:"Ed25519"}, false, ["verify"]);
      const verified = await crypto.subtle.verify("Ed25519", key, decode(signature),
        new TextEncoder().encode("vmarket-ai-context:v1."+encoded));
      const now = Date.now()/1000, deadline = Date.parse(claims.deadline_at)/1000;
      if (!verified || now < claims.issued_at || now-claims.issued_at > 30 || claims.expires_at < claims.issued_at ||
          claims.expires_at > claims.issued_at+30 || now >= claims.expires_at || claims.expires_at > deadline ||
          now >= deadline || claims.operation !== operations[url.pathname] || claims.request_id !== request.headers.get("X-Request-ID")) throw new Error("context");
      const reader = request.body?.getReader();
      const chunks: Uint8Array[] = []; let total = 0;
      if (reader) {
        try {
          while (true) {
            const {done,value} = await reader.read(); if (done) break;
            total += value.length;
            if (total > 65536) { await reader.cancel(); return {success:false,error:{code:"INPUT_TOO_LARGE",status:413,recoverable:false}}; }
            chunks.push(value);
          }
        } finally { reader.releaseLock(); }
      }
      const bytes = new Uint8Array(total); let offset=0;
      for (const chunk of chunks) {bytes.set(chunk,offset);offset+=chunk.length;}
      const digest = await hash(new TextEncoder().encode(["vmarket-ai-request:v1","POST",url.pathname,"application/json",
        ...Array(7).fill(""),await hash(bytes),""].join("\n")));
      if (claims.request_digest !== digest) throw new Error("body");
      return {success:true,claims,bodyText:new TextDecoder("utf-8",{fatal:true,ignoreBOM:true}).decode(bytes)};
    } catch { return {success:false,error:{code:"ACCESS_DENIED",status:401,recoverable:false}}; }
  }
}
