import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

let lastSuccess = 0;

// Vercel's daily cron reaches Postgres even while Render is asleep. This
// public health probe returns no rows and uses only the publishable key + RLS.
export async function GET(request: Request) {
  const secret = process.env.CRON_SECRET;
  if (secret && request.headers.get("authorization") !== `Bearer ${secret}`) {
    return NextResponse.json({ status: "unauthorized" }, { status: 401 });
  }

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) {
    return NextResponse.json({ status: "unconfigured" }, { status: 503 });
  }

  if (Date.now() - lastSuccess >= 60_000) {
    try {
      const response = await fetch(
        `${url.replace(/\/$/, "")}/rest/v1/datasets?select=id&limit=1`,
        {
          headers: { apikey: key },
          cache: "no-store",
          signal: AbortSignal.timeout(15_000),
        },
      );
      if (!response.ok || !Array.isArray(await response.json())) {
        throw new Error("Database unavailable");
      }
      lastSuccess = Date.now();
    } catch {
      return NextResponse.json({ status: "unavailable" }, { status: 503 });
    }
  }

  return NextResponse.json(
    { status: "ok", database: "ok" },
    { headers: { "Cache-Control": "no-store" } },
  );
}
