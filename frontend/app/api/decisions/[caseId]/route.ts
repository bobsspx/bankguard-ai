import {
  NextRequest,
} from "next/server";

import {
  proxyBackendGet,
} from "@/lib/backend-proxy";


type RouteContext = {
  params: Promise<{
    caseId: string;
  }>;
};


export async function GET(
  _request: NextRequest,
  context: RouteContext,
) {
  const {
    caseId,
  } =
    await context.params;

  return proxyBackendGet(
    `/api/v1/decisions/${
      encodeURIComponent(
        caseId,
      )
    }`,
  );
}