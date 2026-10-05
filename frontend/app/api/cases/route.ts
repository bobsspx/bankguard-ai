import {
  NextRequest,
} from "next/server";

import {
  proxyBackendGet,
  proxyBackendJson,
} from "@/lib/backend-proxy";


export async function GET(
  request: NextRequest,
) {
  const search =
    request.nextUrl
      .searchParams
      .toString();

  const path =
    "/api/v1/cases" +
    (
      search
        ? `?${search}`
        : ""
    );

  return proxyBackendGet(
    path,
  );
}


export async function POST(
  request: NextRequest,
) {
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
    "/api/v1/cases",
    "POST",
    body,
  );
}