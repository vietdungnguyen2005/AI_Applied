import { AiGatewayHandler } from "./handler";
import { type CloudEnv, uuid } from "./spec";

export default {
  async scheduled(_event:unknown,env:CloudEnv):Promise<void>{
    if(!env.DB)return;
    const now=Math.floor(Date.now()/1000),today=new Date().toISOString().slice(0,10);
    await env.DB.batch([
      env.DB.prepare(`UPDATE runs SET status='expired',revision=revision+1,event_kind='expire',
        payload=json_set(payload,'$.status','expired','$.phase','terminal','$.revision',revision+1,'$.updated_at',?,
          '$.question','','$.history',json('[]'),'$.summaries',json('[]'),'$.pending',NULL,'$.outcome',NULL,
          '$.reason','TTL_EXPIRED','$.lease_id',NULL,'$.lease_until',NULL)
        WHERE id IN(SELECT id FROM runs WHERE expires_at<=? AND status!='expired' LIMIT 100)` ).bind(now,now),
      env.DB.prepare("DELETE FROM runs WHERE id IN(SELECT id FROM runs WHERE purge_after<=? LIMIT 100)").bind(now),
      env.DB.prepare("DELETE FROM nonces WHERE rowid IN(SELECT rowid FROM nonces WHERE expires_at<? LIMIT 1000)").bind(now-60),
      env.DB.prepare("DELETE FROM budgets WHERE bucket IN(SELECT bucket FROM budgets WHERE (bucket LIKE 'daily:%' AND bucket<?) OR (bucket LIKE 'minute:%' AND CAST(substr(bucket,8,instr(substr(bucket,8),':')-1) AS INTEGER)<?) LIMIT 1000)")
        .bind("daily:"+today,Math.floor(now/60)-2),
    ]);
  },
  async fetch(request: Request, env: CloudEnv): Promise<Response> {
    const result = await new AiGatewayHandler(env).execute(request);
    const requestedTrace = request.headers.get("X-Request-ID");
    const trace = uuid.safeParse(requestedTrace).success ? requestedTrace! : crypto.randomUUID();
    return Response.json(result.success ? result.data.body : {code: result.error.code}, {
      status: result.success ? result.data.status : result.error.status,
      headers: {"Cache-Control": "no-store", "X-Request-ID": trace},
    });
  },
};
