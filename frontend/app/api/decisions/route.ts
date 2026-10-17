import {
  NextRequest,
} from "next/server";

import {
  proxyBackendJson,
} from "@/lib/backend-proxy";


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
    "/api/v1/decisions",
    "POST",
    body,
  );
}