import {
  NextRequest,
} from "next/server";

import {
  proxyBackendJson,
} from "@/lib/backend-proxy";
import { rejectCrossOrigin } from "@/lib/request-origin";


export async function POST(
  request: NextRequest,
) {
  const originError = rejectCrossOrigin(request);
  if (originError) return originError;
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
