import { createHash, generateKeyPairSync, sign } from "node:crypto";
export const key = generateKeyPairSync("ed25519");
export const publicKeys = JSON.stringify({cloud: key.publicKey.export({type: "spki", format: "der"}).subarray(-32).toString("base64")});
export function signed(path: string, body: string, updates: Record<string, unknown> = {}): Request {
  const now = Math.floor(Date.now()/1000);
  const digest = createHash("sha256").update(["vmarket-ai-request:v1", "POST", path, "application/json",
    ...Array(7).fill(""), createHash("sha256").update(body).digest("hex"), ""].join("\n")).digest("hex");
  const claims = {version: 1, issuer: "vmarket-bff", audience: "vmarket-ai", mode: "integrated", kid: "cloud",
    actor_ref: "a".repeat(64), request_id: crypto.randomUUID(), run_id: crypto.randomUUID(), step: 0,
    collection_ids: ["4aa83e9f-0a0a-5558-8f5e-0f87db27c923"], deadline_at: new Date((now+25)*1000).toISOString(),
    issued_at: now, expires_at: now+25, operation: "ask", nonce: crypto.randomUUID(), request_digest: digest, ...updates};
  const encoded = Buffer.from(JSON.stringify(claims)).toString("base64url");
  return new Request("https://ai.example"+path, {method: "POST", body, headers: {
    "Content-Type": "application/json", "X-Request-ID": String(claims.request_id), "X-AI-Context": encoded,
    "X-AI-Signature": sign(null, Buffer.from("vmarket-ai-context:v1."+encoded), key.privateKey).toString("base64url"),
  }});
}
