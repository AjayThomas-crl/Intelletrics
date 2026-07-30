import Link from "next/link";
import { ArrowLeft, History } from "lucide-react";

export default function HistoryPage() {
  return (
    <div className="flex min-h-full flex-1 items-center justify-center p-6">
      <div className="flex max-w-md flex-col items-center text-center">
        <div className="mb-4 flex size-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
          <History className="size-5" />
        </div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          History
        </p>
        <h1 className="text-2xl font-semibold tracking-tight">Coming soon</h1>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Previously uploaded datasets and their analysis results will appear here.
        </p>
        <Link
          href="/dashboard"
          className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline"
        >
          <ArrowLeft className="size-4" />
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}
