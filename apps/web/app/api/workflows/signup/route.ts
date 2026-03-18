import { NextResponse } from "next/server";

import { handleUserSignup } from "@/lib/workflows/user-signup";

export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as { email?: string };
  const email = typeof body.email === "string" ? body.email.trim() : "";

  if (!email) {
    return NextResponse.json({ error: "email is required" }, { status: 400 });
  }

  const result = await handleUserSignup(email);
  return NextResponse.json(result, { status: 202 });
}
