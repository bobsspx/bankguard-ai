import DashboardClient from "./dashboard-client";


export default async function Home({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const incoming = await searchParams;
  const params = new URLSearchParams();
  for (const key of ["account_ref", "country_code", "channel", "min_amount", "offset", "sort_by", "sort_dir"]) {
    const value = incoming[key];
    if (typeof value === "string") params.set(key, value);
  }
  return (
    <DashboardClient initialQuery={params.toString()} />
  );
}
