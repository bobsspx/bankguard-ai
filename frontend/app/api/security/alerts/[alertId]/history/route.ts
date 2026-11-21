import { proxyBackendGet } from "@/lib/backend-proxy";

export async function GET(request: Request, context: { params: Promise<{ alertId: string }> }) {
  const { alertId } = await context.params;
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(alertId)) {
    return Response.json({ error: "Invalid alert ID." }, { status: 422 });
  }
  const input = new URL(request.url).searchParams;
  const query = new URLSearchParams();
  for (const key of ["limit", "offset"]) {
    if (input.has(key)) query.set(key, input.get(key)!);
  }
  return proxyBackendGet(`/api/v1/security/alerts/${alertId}/history?${query}`);
}
