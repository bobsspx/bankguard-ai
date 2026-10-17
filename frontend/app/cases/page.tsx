import CasesClient from "./cases-client";
import { Suspense } from "react";

export default function CasesPage() {
  return (
    <Suspense fallback={<p>Loading investigations...</p>}>
      <CasesClient />
    </Suspense>
  );
}
