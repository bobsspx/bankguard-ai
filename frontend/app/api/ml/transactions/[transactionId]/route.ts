import { NextResponse } from "next/server";
import { proxyBackendGet } from "@/lib/backend-proxy";

export async function GET(
  _request: Request,
  context: { params: Promise<{ transactionId: string }> },
) {
  const { transactionId } = await context.params;
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(transactionId)) {
    return NextResponse.json({ detail: "Invalid transaction UUID." }, { status: 400 });
  }
  return proxyBackendGet(`/api/v1/ml/transactions/${transactionId}`);
}
