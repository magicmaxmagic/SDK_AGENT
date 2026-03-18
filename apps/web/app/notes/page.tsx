import { createClient, hasSupabaseEnv } from "@/lib/supabase/server";

export default async function NotesPage() {
  if (!hasSupabaseEnv()) {
    return (
      <main>
        <section className="card">
          <h1>Configuration requise</h1>
          <p>Supabase n est pas configure. Ajoute les variables dans `.env.local` ou Vercel.</p>
        </section>
      </main>
    );
  }

  const supabase = await createClient();
  const { data: notes, error } = await supabase.from("notes").select("id,title").order("id", { ascending: true });

  return (
    <main>
      <section className="card">
        <h1>Notes</h1>
        {error ? (
          <pre>{JSON.stringify({ error: error.message }, null, 2)}</pre>
        ) : (
          <pre>{JSON.stringify(notes, null, 2)}</pre>
        )}
      </section>
    </main>
  );
}
