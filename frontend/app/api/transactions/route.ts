import { cookies } from "next/headers";
import {
  NextRequest,
  NextResponse,
} from "next/server";


const API_URL =
  process.env.BANKGUARD_API_URL ??
  "http://127.0.0.1:8000";


export async function GET(
  request: NextRequest,
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

  const search =
    request.nextUrl.searchParams
      .toString();

  const url =
    `${API_URL}/api/v1/transactions` +
    (search ? `?${search}` : "");

  let response: Response;

  try {
    response = await fetch(
      url,
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
          "Transaction service unavailable.",
      },
      {
        status: 503,
      },
    );
  }

  const data =
    await response.json();

  return NextResponse.json(
    data,
    {
      status: response.status,
    },
  );
}