import { NextResponse } from "next/server";


export async function POST() {
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