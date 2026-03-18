import { NextResponse } from "next/server";

import { createClient, hasSupabaseEnv } from "@/lib/supabase/server";

export async function GET() {
  if (!hasSupabaseEnv()) {
    return NextResponse.json({ error: "Supabase environment is not configured" }, { status: 500 });
  }

  const supabase = await createClient();
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();

  if (error || !user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  return NextResponse.json({
    ok: true,
    message: "Backend authentifie avec Supabase",
    user: {
      id: user.id,
      email: user.email,
    },
  });
}
