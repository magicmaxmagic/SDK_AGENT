import Link from "next/link";
import { redirect } from "next/navigation";

import { createClient, hasSupabaseEnv } from "@/lib/supabase/server";

import { signOutAction } from "../login/actions";
import NoteForm from "./note-form";
import OrganizationForm from "./organization-form";
import ProjectForm from "./project-form";
import SubscriptionForm from "./subscription-form";

export default async function DashboardPage() {
  if (!hasSupabaseEnv()) {
    return (
      <main>
        <section className="card">
          <h1>Configuration requise</h1>
          <p>Supabase n&apos;est pas configure. Ajoute les variables dans `.env.local` ou Vercel.</p>
          <p>
            <Link href="/login">Aller a la page de connexion</Link>
          </p>
        </section>
      </main>
    );
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data: notes, error: notesError } = await supabase
    .from("notes")
    .select("id,title")
    .order("id", { ascending: false })
    .limit(10);

  const { data: memberships } = await supabase
    .from("organization_memberships")
    .select("organization_id,role")
    .eq("user_id", user.id);
  const organizationIds = (memberships ?? []).map((item) => item.organization_id);

  const { data: organizations } = await supabase
    .from("organizations")
    .select("id,name,slug")
    .in("id", organizationIds.length > 0 ? organizationIds : ["00000000-0000-0000-0000-000000000000"])
    .order("created_at", { ascending: false });

  const { data: projects } = await supabase
    .from("projects")
    .select("id,name,slug,organization_id")
    .in("organization_id", organizationIds.length > 0 ? organizationIds : ["00000000-0000-0000-0000-000000000000"])
    .order("created_at", { ascending: false })
    .limit(12);

  const { data: subscriptions } = await supabase
    .from("subscriptions")
    .select("organization_id,plan,status,seats,trial_ends_at")
    .in("organization_id", organizationIds.length > 0 ? organizationIds : ["00000000-0000-0000-0000-000000000000"]);

  const notesCount = notes?.length ?? 0;
  const orgCount = organizations?.length ?? 0;
  const projectCount = projects?.length ?? 0;
  const subscriptionCount = subscriptions?.length ?? 0;
  const apiStatus = "online";

  return (
    <main>
      <div className="header">
        <h1>Workspace SaaS</h1>
        <form action={signOutAction}>
          <button type="submit">Se deconnecter</button>
        </form>
      </div>

      <section className="dashboard-grid">
        <article className="card stat-card">
          <p className="muted-label">Utilisateur</p>
          <p className="stat-value">{user.email}</p>
          <p className="muted-label">ID: {user.id}</p>
        </article>

        <article className="card stat-card">
          <p className="muted-label">Organisations / Projets</p>
          <p className="stat-value">{orgCount} / {projectCount}</p>
          <p className="muted-label">Tenant scope courant</p>
        </article>

        <article className="card stat-card">
          <p className="muted-label">Backend prive</p>
          <p className="stat-value">{apiStatus}</p>
          <p>
            Endpoint: <Link href="/api/private">/api/private</Link>
          </p>
        </article>

        <article className="card stat-card">
          <p className="muted-label">Subscriptions</p>
          <p className="stat-value">{subscriptionCount}</p>
          <p className="muted-label">Actives sur mes organisations</p>
        </article>

        <article className="card stat-card">
          <p className="muted-label">Notes recentes</p>
          <p className="stat-value">{notesCount}</p>
          <p className="muted-label">Top 10 chargees</p>
        </article>
      </section>

      <section className="dashboard-columns">
        <article className="card">
          <div className="section-header">
            <h2>Activite Notes</h2>
            <Link href="/notes">Voir la page notes</Link>
          </div>
          {notesError ? (
            <p className="error-text">Erreur notes: {notesError.message}</p>
          ) : notesCount === 0 ? (
            <p>Aucune note pour le moment.</p>
          ) : (
            <ul className="notes-list">
              {notes?.map((note) => (
                <li key={note.id} className="note-item">
                  <span className="note-id">#{note.id}</span>
                  <span>{note.title}</span>
                </li>
              ))}
            </ul>
          )}
        </article>

        <div className="form-stack">
          <OrganizationForm />
          <ProjectForm organizations={organizations ?? []} />
          <SubscriptionForm organizations={organizations ?? []} />
          <NoteForm />
        </div>
      </section>

      <section className="dashboard-columns">
        <article className="card">
          <div className="section-header">
            <h2>Organisations</h2>
          </div>
          {orgCount === 0 ? (
            <p>Aucune organisation.</p>
          ) : (
            <ul className="notes-list">
              {organizations?.map((org) => {
                const role = memberships?.find((item) => item.organization_id === org.id)?.role ?? "member";
                return (
                  <li key={org.id} className="note-item">
                    <span className="note-id">{role}</span>
                    <span>{org.name} ({org.slug})</span>
                  </li>
                );
              })}
            </ul>
          )}
        </article>

        <article className="card">
          <div className="section-header">
            <h2>Projects</h2>
          </div>
          {projectCount === 0 ? (
            <p>Aucun projet.</p>
          ) : (
            <ul className="notes-list">
              {projects?.map((project) => {
                const orgName = organizations?.find((org) => org.id === project.organization_id)?.name ?? "org";
                return (
                  <li key={project.id} className="note-item">
                    <span className="note-id">{orgName}</span>
                    <span>{project.name} ({project.slug})</span>
                  </li>
                );
              })}
            </ul>
          )}
        </article>
      </section>

      <section>
        <article className="card">
          <div className="section-header">
            <h2>Subscriptions</h2>
          </div>
          {subscriptionCount === 0 ? (
            <p>Aucune subscription.</p>
          ) : (
            <ul className="notes-list">
              {subscriptions?.map((subscription) => {
                const orgName = organizations?.find((org) => org.id === subscription.organization_id)?.name ?? "org";
                return (
                  <li key={subscription.organization_id} className="note-item">
                    <span className="note-id">{subscription.plan}</span>
                    <span>{orgName} | {subscription.status} | {subscription.seats} seats</span>
                  </li>
                );
              })}
            </ul>
          )}
        </article>
      </section>
    </main>
  );
}
