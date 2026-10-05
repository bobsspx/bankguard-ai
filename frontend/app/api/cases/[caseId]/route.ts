import {
  NextRequest,
} from "next/server";

import {
  proxyBackendGet,
  proxyBackendJson,
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
    `/api/v1/cases/${
      encodeURIComponent(
        caseId,
      )
    }`,
  );
}


export async function PATCH(
  request: NextRequest,
  context: RouteContext,
) {
  const {
    caseId,
  } =
    await context.params;

  let body: unknown;

  try {
    body =
      await request.json();

  } catch {
    return Response.json(
      {
        error:
          "Invalid JSON body.",
      },
      {
        status: 400,
      },
    );
  }

  return proxyBackendJson(
    `/api/v1/cases/${
      encodeURIComponent(
        caseId,
      )
    }`,
    "PATCH",
    body,
  );
}