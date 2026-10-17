import MLInspectionClient from "./ml-inspection-client";

export default async function TransactionInspectionPage({
  params,
}: {
  params: Promise<{ transactionId: string }>;
}) {
  const { transactionId } = await params;
  return <MLInspectionClient key={transactionId} transactionId={transactionId} />;
}
