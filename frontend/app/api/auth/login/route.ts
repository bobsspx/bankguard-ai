import { NextResponse } from "next/server";
import { rejectCrossOrigin } from "@/lib/request-origin";

const API_URL =
  process.env.BANKGUARD_API_URL ??
  "http://127.0.0.1:8000";

export async function POST(request: Request) {
  const originError = rejectCrossOrigin(request);
  if (originError) return originError;
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return NextResponse.json({ error: "Invalid login body." }, { status: 400 });
  }

  const login = body as Record<string, unknown>;

  const email =
    typeof login.email === "string"
      ? login.email.trim()
      : "";

  const password =
    typeof login.password === "string"
      ? login.password
      : "";

  if (!email || !password) {
    return NextResponse.json(
      {
        error: "Email and password are required.",
      },
      {
        status: 400,
      },
    );
  }

  const form = new URLSearchParams();

  form.set(
    "username",
    email,
  );

  form.set(
    "password",
    password,
  );

  let response: Response;

  try {
    response = await fetch(
      `${API_URL}/api/v1/auth/login`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/x-www-form-urlencoded",
        },

        body: form,

        cache: "no-store",
      },
    );
  } catch {
    return NextResponse.json(
      {
        error: "Authentication service unavailable.",
      },
      {
        status: 503,
      },
    );
  }

  if (!response.ok) {
    if (response.status === 429) {
      const retryAfter = response.headers.get("Retry-After");
      return NextResponse.json(
        { error: "Too many login attempts. Please try again later." },
        { status: 429, headers: retryAfter ? { "Retry-After": retryAfter } : {} },
      );
    }
    if (response.status >= 500) {
      return NextResponse.json(
        { error: "Authentication service unavailable." },
        { status: 503 },
      );
    }
    return NextResponse.json(
      {
        error: "Invalid credentials.",
      },
      {
        status: 401,
      },
    );
  }

  const data = await response.json();

  const result = NextResponse.json({
    status: "ok",
  });

  result.cookies.set({
    name: "bankguard_access_token",

    value: data.access_token,

    httpOnly: true,

    secure:
      process.env.NODE_ENV ===
      "production",

    sameSite: "strict",

    path: "/",

    maxAge: 60 * 30,
  });

  return result;
}
