"use server";

import { revalidatePath } from "next/cache";

import { createClient, hasSupabaseEnv } from "@/lib/supabase/server";

export type DashboardActionResult = { ok: boolean; message: string } | null;

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
}

export async function createNoteAction(_prevState: DashboardActionResult, formData: FormData) {
  if (!hasSupabaseEnv()) {
    return { ok: false, message: "Supabase n est pas configure" };
  }

  const title = String(formData.get("title") || "").trim();
  if (!title) {
    return { ok: false, message: "Le titre est requis" };
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return { ok: false, message: "Session invalide. Reconnecte toi." };
  }

  const { error } = await supabase.from("notes").insert({ title, created_by: user.id });
  if (error) {
    return { ok: false, message: error.message };
  }

  revalidatePath("/dashboard");
  revalidatePath("/notes");
  return { ok: true, message: "Note ajoutee" };
}

export async function createOrganizationAction(_prevState: DashboardActionResult, formData: FormData) {
  if (!hasSupabaseEnv()) {
    return { ok: false, message: "Supabase n est pas configure" };
  }

  const name = String(formData.get("name") || "").trim();
  const slugInput = String(formData.get("slug") || "").trim();
  const slug = slugify(slugInput || name);
  if (!name || !slug) {
    return { ok: false, message: "Nom et slug valides requis" };
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return { ok: false, message: "Session invalide. Reconnecte toi." };
  }

  const { data: org, error: orgError } = await supabase
    .from("organizations")
    .insert({ name, slug, created_by: user.id })
    .select("id")
    .single();

  if (orgError || !org) {
    return { ok: false, message: orgError?.message ?? "Creation organisation impossible" };
  }

  const { error: memberError } = await supabase
    .from("organization_memberships")
    .insert({ organization_id: org.id, user_id: user.id, role: "owner" });

  if (memberError) {
    return { ok: false, message: memberError.message };
  }

  revalidatePath("/dashboard");
  return { ok: true, message: "Organisation creee" };
}

export async function createProjectAction(_prevState: DashboardActionResult, formData: FormData) {
  if (!hasSupabaseEnv()) {
    return { ok: false, message: "Supabase n est pas configure" };
  }

  const organizationId = String(formData.get("organization_id") || "").trim();
  const name = String(formData.get("name") || "").trim();
  const slugInput = String(formData.get("slug") || "").trim();
  const slug = slugify(slugInput || name);

  if (!organizationId || !name || !slug) {
    return { ok: false, message: "Organisation, nom et slug requis" };
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return { ok: false, message: "Session invalide. Reconnecte toi." };
  }

  const { data: membership } = await supabase
    .from("organization_memberships")
    .select("role")
    .eq("organization_id", organizationId)
    .eq("user_id", user.id)
    .maybeSingle();

  const role = membership?.role ?? "";
  if (!role || (role !== "owner" && role !== "admin")) {
    return { ok: false, message: "Permissions insuffisantes pour creer un projet" };
  }

  const { error } = await supabase.from("projects").insert({
    organization_id: organizationId,
    name,
    slug,
    created_by: user.id,
  });

  if (error) {
    return { ok: false, message: error.message };
  }

  revalidatePath("/dashboard");
  return { ok: true, message: "Projet cree" };
}

export async function upsertSubscriptionAction(_prevState: DashboardActionResult, formData: FormData) {
  if (!hasSupabaseEnv()) {
    return { ok: false, message: "Supabase n est pas configure" };
  }

  const organizationId = String(formData.get("organization_id") || "").trim();
  const plan = String(formData.get("plan") || "free").trim();
  const status = String(formData.get("status") || "trialing").trim();
  const seats = Number(String(formData.get("seats") || "1"));

  if (!organizationId || !Number.isFinite(seats) || seats < 1) {
    return { ok: false, message: "Organisation et nombre de sieges valides requis" };
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return { ok: false, message: "Session invalide. Reconnecte toi." };
  }

  const { data: membership } = await supabase
    .from("organization_memberships")
    .select("role")
    .eq("organization_id", organizationId)
    .eq("user_id", user.id)
    .maybeSingle();
  const role = membership?.role ?? "";
  if (!role || (role !== "owner" && role !== "admin")) {
    return { ok: false, message: "Permissions insuffisantes pour modifier la subscription" };
  }

  const { error } = await supabase.from("subscriptions").upsert(
    {
      organization_id: organizationId,
      plan,
      status,
      seats,
      trial_ends_at: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString(),
    },
    { onConflict: "organization_id" }
  );

  if (error) {
    return { ok: false, message: error.message };
  }

  revalidatePath("/dashboard");
  return { ok: true, message: "Subscription mise a jour" };
}
