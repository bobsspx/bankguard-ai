import TransactionDetailClient from "./transaction-detail-client";
import { readTransactionQuery, transactionQuery } from "@/lib/transaction-query";

export default async function TransactionInspectionPage({
  params,
  searchParams,
}: {
  params: Promise<{ transactionId: string }>;
  searchParams: Promise<{ return?: string | string[] }>;
}) {
  const { transactionId } = await params;
  const requestedReturn = (await searchParams).return;
  let backHref = "/";
  if (typeof requestedReturn === "string" && requestedReturn.startsWith("?") && !requestedReturn.startsWith("?//")) {
    const { filters, offset, sortBy, sortDir } = readTransactionQuery(new URLSearchParams(requestedReturn));
    const query = transactionQuery(filters, offset, sortBy, sortDir);
    query.delete("limit");
    backHref = `/?${query}`;
  }
  return <TransactionDetailClient key={transactionId} transactionId={transactionId} backHref={backHref} />;
}
