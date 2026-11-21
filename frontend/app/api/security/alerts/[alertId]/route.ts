import { proxyBackendGet, proxyBackendJson } from "@/lib/backend-proxy";
import { rejectCrossOrigin } from "@/lib/request-origin";

type Context = { params: Promise<{ alertId: string }> };
const validId = (id: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);

export async function GET(_request: Request, context: Context) {
  const { alertId } = await context.params;
  if (!validId(alertId)) return Response.json({ error: "Invalid alert ID." }, { status: 422 });
  return proxyBackendGet(`/api/v1/security/alerts/${alertId}`);
}

export async function PATCH(request: Request, context: Context) {
  const { alertId } = await context.params;
  if (!validId(alertId)) return Response.json({ error: "Invalid alert ID." }, { status: 422 });
  const originError = rejectCrossOrigin(request);
  if (originError) return originError;
  let body: unknown;
  try { body = await request.json(); }
  catch { return Response.json({ error: "Invalid JSON." }, { status: 400 }); }
  return proxyBackendJson(`/api/v1/security/alerts/${alertId}`, "PATCH", body);
}
