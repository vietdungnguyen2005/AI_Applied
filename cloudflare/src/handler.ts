import { type AiGatewaySpec, type CloudEnv, type GatewayResult, RequestInput, fail } from "./spec";
import { AuthenticationHandler } from "./authentication";
import { strictJson } from "./json";
import { CitationHandler } from "./knowledge";
import { AskHandler } from "./qa";

export class AiGatewayHandler implements AiGatewaySpec {
  constructor(private readonly env: CloudEnv) {}
  async execute(input: Request): Promise<GatewayResult> {
    try {
      const parsed = RequestInput.safeParse(input);
      if (!parsed.success) return fail("INPUT_INVALID", 400);
      if (input.method === "GET" && new URL(input.url).pathname === "/health") {
        return {success:true,data:{status:200,body:{status:"ok"}}};
      }
      if (input.method === "GET" && new URL(input.url).pathname === "/ready") {
        if (!this.env.DB || !this.env.PUBLIC_KEYS_JSON || !this.env.AI) return fail("CONFIGURATION_UNAVAILABLE",503);
        const row = await this.env.DB.prepare("SELECT version FROM schema_meta WHERE version=1").first<{version:number}>();
        if (!row) return fail("DEPENDENCY_UNAVAILABLE",503);
        return {success:true,data:{status:200,body:{status:"ready"}}};
      }
      const authentication = await new AuthenticationHandler(this.env.PUBLIC_KEYS_JSON).execute(input);
      if (!authentication.success) return authentication;
      let body: unknown;
      try { body = strictJson(authentication.bodyText); } catch { return fail("INPUT_INVALID", 400); }
      if (body && typeof body === "object" && "collection_ids" in body) {
        const ids = (body as {collection_ids: unknown}).collection_ids;
        if (Array.isArray(ids) && ids.some(id => !authentication.claims.collection_ids.includes(id))) {
          return fail("ACCESS_DENIED", 403);
        }
      }
      if (!this.env.DB) return fail("CONFIGURATION_UNAVAILABLE", 503);
      const { kid, nonce, expires_at } = authentication.claims;
      const consumed = await this.env.DB.prepare(
        "INSERT INTO nonces(kid,nonce,expires_at) VALUES(?,?,?) ON CONFLICT DO NOTHING RETURNING nonce",
      ).bind(kid, nonce, expires_at).first<{nonce: string}>();
      if (!consumed) return fail("STEP_CONFLICT", 409);
      if (authentication.claims.operation === "documents_read") {
        return new CitationHandler(this.env.DB).execute(body,authentication.claims);
      }
      if (authentication.claims.operation === "ask") {
        return new AskHandler(this.env).execute(body,authentication.claims);
      }
      return fail("CONFIGURATION_UNAVAILABLE", 503);
    } catch { return fail("DEPENDENCY_UNAVAILABLE", 503); }
  }
}
