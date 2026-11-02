import { z } from "zod";

export const RequestInput = z.instanceof(Request);
export const HttpOutput = z.strictObject({status: z.number().int().min(200).max(299), body: z.record(z.string(), z.unknown())});
export const ErrorCode = z.enum(["ACCESS_DENIED", "INPUT_INVALID", "INPUT_TOO_LARGE", "STEP_CONFLICT",
  "DEADLINE_EXCEEDED", "DEPENDENCY_UNAVAILABLE", "CONFIGURATION_UNAVAILABLE", "BUDGET_EXCEEDED",
  "OUTPUT_INVALID", "DOCUMENT_NOT_AVAILABLE", "RUN_NOT_AVAILABLE", "RESOURCE_NOT_AVAILABLE"]);
export const Failure = z.strictObject({success: z.literal(false), error: z.strictObject({
  code: ErrorCode, status: z.number().int().min(400).max(599), recoverable: z.boolean(),
})});
export const Success = z.strictObject({success: z.literal(true), data: HttpOutput});
export type GatewayResult = z.infer<typeof Success> | z.infer<typeof Failure>;
export type SqlValue = string | number | null | ArrayBuffer;
export interface SqlResult { success: boolean; meta: {changes: number}; results?: Record<string,unknown>[] }
export interface Statement {
  bind(...values: SqlValue[]): Statement;
  first<T>(): Promise<T | null>;
  all<T>(): Promise<{results: T[]}>;
  run(): Promise<SqlResult>;
}
export interface Database {
  prepare(sql: string): Statement;
  batch(statements: Statement[]): Promise<SqlResult[]>;
}
export interface AiBinding {run(model:string,input:Record<string,unknown>):Promise<unknown>}
export interface CloudEnv { PUBLIC_KEYS_JSON?: string; DB?: Database; AI?:AiBinding }
export interface AiGatewaySpec { execute(input: Request): Promise<GatewayResult> }
export const uuid = z.string().regex(/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/);
export const collections = z.array(uuid).min(1).max(10).refine(ids => new Set(ids).size === ids.length);
export const AskInput = z.strictObject({question:z.string().min(1).max(2000).refine(q=>Boolean(q.trim())),
  collection_ids:collections,language:z.enum(["en","ja"])});
export const Context = z.strictObject({version: z.literal(1), issuer: z.literal("vmarket-bff"), audience: z.literal("vmarket-ai"),
  mode: z.literal("integrated"), kid: z.string().regex(/^[A-Za-z0-9_-]{1,32}$/),
  actor_ref: z.string().regex(/^[0-9a-f]{64}$/), request_id: uuid, run_id: uuid, step: z.number().int().min(0).max(3),
  collection_ids: z.array(uuid).max(10), deadline_at: z.iso.datetime({offset: true}),
  nonce: uuid, issued_at: z.number().int().nonnegative(), expires_at: z.number().int().nonnegative(),
  operation: z.enum(["ask", "documents_read", "knowledge_search", "agent_step", "run_control", "mapping_suggest"]),
  request_digest: z.string().regex(/^[a-f0-9]{64}$/),
});
export type Claims = z.infer<typeof Context>;
export type AuthResult = {success: true; claims: Claims; bodyText: string} | z.infer<typeof Failure>;
export interface AuthenticationSpec { execute(input: Request): Promise<AuthResult> }
export const fail = (code: z.infer<typeof ErrorCode>, status: number): GatewayResult => ({
  success: false, error: {code, status, recoverable: status >= 500 || status === 429},
});
