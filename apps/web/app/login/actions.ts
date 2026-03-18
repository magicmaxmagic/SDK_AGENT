"use server";

import { redirect } from "next/navigation";

import { createClient } from "@/lib/supabase/server";

type ActionResult = { ok: boolean; message: string } | null;

export async function signInAction(_prevState: ActionResult, formData: FormData) {
  const email = String(formData.get("email") || "").trim();
  const password = String(formData.get("password") || "").trim();

  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });

  if (error) {
    return { ok: false, message: error.message };
  }

  redirect("/dashboard");
}

export async function signUpAction(_prevState: ActionResult, formData: FormData) {
  const email = String(formData.get("email") || "").trim();
  const password = String(formData.get("password") || "").trim();

  const supabase = await createClient();
  const { error } = await supabase.auth.signUp({ email, password });

  if (error) {
    return { ok: false, message: error.message };
  }

  return {
    ok: true,
    message: "Compte cree. Si la confirmation email est activee, verifie ta boite mail.",
  };
}

export async function signOutAction() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}
