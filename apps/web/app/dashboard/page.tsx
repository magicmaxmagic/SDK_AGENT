import Link from "next/link";
import { redirect } from "next/navigation";

import { createClient, hasSupabaseEnv } from "@/lib/supabase/server";

import { signOutAction } from "../login/actions";

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

  return (
    <main>
      <div className="header">
        <h1>Dashboard prive</h1>
        <form action={signOutAction}>
          <button type="submit">Se deconnecter</button>
        </form>
      </div>

      <section className="card">
        <p>
          Connecte en tant que: <strong>{user.email}</strong>
        </p>
        <p>
          Le backend protege est disponible ici: <Link href="/api/private">/api/private</Link>
        </p>
      </section>
    </main>
  );
}
