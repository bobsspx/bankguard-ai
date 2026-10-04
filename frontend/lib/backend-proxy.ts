import "server-only";

import { cookies } from "next/headers";
import { NextResponse } from "next/server";


const API_URL =
  process.env.BANKGUARD_API_URL ??
  "http://127.0.0.1:8000";


export async function
proxyBackendGet(
  path: string,
) {
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
      `${API_URL}${path}`,
      {
        method: "GET",

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
          "BankGuard API unavailable.",
      },
      {
        status: 503,
      },
    );
  }

  let data: unknown;

  try {
    data =
      await response.json();

  } catch {
    data = {
      error:
        "Invalid API response.",
    };
  }

  return NextResponse.json(
    data,
    {
      status: response.status,

      headers: {
        "Cache-Control":
          "no-store",
      },
    },
  );
}