import { cookies } from "next/headers";
import { NextResponse } from "next/server";


const API_URL =
  process.env.BANKGUARD_API_URL ??
  "http://127.0.0.1:8000";


export async function GET() {
  const cookieStore =
    await cookies();

  const token =
    cookieStore.get(
      "bankguard_access_token",
    )?.value;

  if (!token) {
    return NextResponse.json(
      {
        error: "Unauthenticated.",
      },
      {
        status: 401,
      },
    );
  }

  let response: Response;

  try {
    response = await fetch(
      `${API_URL}/api/v1/auth/me`,
      {
        headers: {
          Authorization:
            `Bearer ${token}`,
        },

        cache: "no-store",
      },
    );
  } catch {
    return NextResponse.json(
      {
        error:
          "Authentication service unavailable.",
      },
      {
        status: 503,
      },
    );
  }

  if (!response.ok) {
    return NextResponse.json(
      {
        error: "Session invalid.",
      },
      {
        status: response.status,
      },
    );
  }

  return NextResponse.json(
    await response.json(),
  );
}