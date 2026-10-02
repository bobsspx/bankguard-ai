import { NextResponse } from "next/server";

const API_URL =
  process.env.BANKGUARD_API_URL ??
  "http://127.0.0.1:8000";

export async function POST(request: Request) {
  const body = await request.json();

  const email =
    typeof body.email === "string"
      ? body.email.trim()
      : "";

  const password =
    typeof body.password === "string"
      ? body.password
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