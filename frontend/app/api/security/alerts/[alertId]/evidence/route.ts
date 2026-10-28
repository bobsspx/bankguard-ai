
import { proxyBackendGet } from "@/lib/backend-proxy";

type RouteContext = {
  params: Promise<{ alertId: string }>;
};

export async function GET(
  _request: Request,
  context: RouteContext
) {
  const { alertId } = await context.params;

  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(alertId)) {
    return Response.json(
      { error: "Invalid alert ID." },
      { status: 422 }
    );
  }

  return proxyBackendGet(
    `/api/v1/security/alerts/${alertId}/evidence`
  );
}
