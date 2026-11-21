export async function revokeAndLogout(
  router: { replace(path: string): void; refresh(): void },
  setError: (message: string) => void,
) {
  try {
    const response = await fetch("/api/auth/logout", { method: "POST" });
    if (!response.ok) throw new Error("Session revocation failed.");
    router.replace("/login");
    router.refresh();
  } catch {
    setError("Unable to revoke session. Please retry logout.");
  }
}
