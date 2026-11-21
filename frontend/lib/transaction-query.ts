export const PAGE_SIZE = 25;
export type TransactionSortBy = "occurred_at" | "amount" | "transaction_ref";
export type TransactionSortDir = "asc" | "desc";

export type TransactionFilters = {
  account: string;
  country: string;
  channel: string;
  minAmount: string;
};

export const emptyTransactionFilters: TransactionFilters = {
  account: "", country: "", channel: "", minAmount: "",
};

export function readTransactionQuery(params: URLSearchParams) {
  const rawOffset = Number(params.get("offset") ?? "0");
  const rawSortBy = params.get("sort_by");
  const rawSortDir = params.get("sort_dir");
  return {
    filters: {
      account: params.get("account_ref") ?? "",
      country: params.get("country_code") ?? "",
      channel: params.get("channel") ?? "",
      minAmount: params.get("min_amount") ?? "",
    },
    offset: Number.isSafeInteger(rawOffset) && rawOffset >= 0 ? rawOffset : 0,
    sortBy: rawSortBy === "amount" || rawSortBy === "transaction_ref" ? rawSortBy : "occurred_at" as TransactionSortBy,
    sortDir: rawSortDir === "asc" ? "asc" : "desc" as TransactionSortDir,
  };
}

export function transactionQuery(filters: TransactionFilters, offset = 0, sortBy: TransactionSortBy = "occurred_at", sortDir: TransactionSortDir = "desc") {
  const params = new URLSearchParams();
  params.set("limit", String(PAGE_SIZE));
  params.set("offset", String(offset));
  if (filters.account.trim()) params.set("account_ref", filters.account.trim());
  if (filters.country.trim()) params.set("country_code", filters.country.trim().toUpperCase());
  if (filters.channel) params.set("channel", filters.channel);
  if (filters.minAmount) params.set("min_amount", filters.minAmount);
  if (sortBy !== "occurred_at" || sortDir !== "desc") {
    params.set("sort_by", sortBy);
    params.set("sort_dir", sortDir);
  }
  return params;
}
