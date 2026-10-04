import {
  NextRequest,
} from "next/server";

import {
  proxyBackendGet,
} from "@/lib/backend-proxy";


export async function GET(
  request: NextRequest,
) {
  const search =
    request.nextUrl
      .searchParams
      .toString();

  const path =
    "/api/v1/fraud/scores" +
    (
      search
        ? `?${search}`
        : ""
    );

  return proxyBackendGet(
    path,
  );
}