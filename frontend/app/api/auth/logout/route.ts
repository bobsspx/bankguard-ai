import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { rejectCrossOrigin } from "@/lib/request-origin";

const API_URL = process.env.BANKGUARD_API_URL ?? "http://127.0.0.1:8000";

export async function POST(request: Request) {
  const originError = rejectCrossOrigin(request);
  if (originError) return originError;

  const token = (await cookies()).get("bankguard_access_token")?.value;
  if (token) {
    let upstream: Response;
    try {
      upstream = await fetch(`${API_URL}/api/v1/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
    } catch {
      return NextResponse.json({ error: "Session revocation unavailable." }, { status: 503 });
    }
    if (!upstream.ok && upstream.status !== 401) {
      return NextResponse.json({ error: "Session revocation unavailable." }, { status: 503 });
    }
  }

  const response =
    NextResponse.json({
      status: "ok",
    });

  response.cookies.set({
    name: "bankguard_access_token",

    value: "",

    httpOnly: true,

    secure:
      process.env.NODE_ENV ===
      "production",

    sameSite: "strict",

    path: "/",

    maxAge: 0,
  });

  return response;
}
