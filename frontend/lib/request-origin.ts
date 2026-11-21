export function isSameOriginRequest(request: Request): boolean {
  const origin = request.headers.get("origin");
  const url = new URL(request.url);
  // Next can normalize its internal URL; Host is the browser destination.
  return origin !== null && origin === `${url.protocol}//${request.headers.get("host") ?? url.host}`;
}

export function rejectCrossOrigin(request: Request): Response | null {
  return isSameOriginRequest(request)
    ? null
    : Response.json({ error: "Invalid request origin." }, { status: 403 });
}
