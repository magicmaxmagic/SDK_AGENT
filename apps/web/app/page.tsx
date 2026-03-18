import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <div className="header">
        <h1>SDK Agent Control Plane</h1>
        <span className="badge">Vercel + Supabase</span>
      </div>

      <section className="card">
        <h2>Stack prête au deploiement</h2>
        <p>
          Frontend Next.js et backend API protege, relies a Supabase Auth.
          Le dashboard et les routes privees exigent une session valide.
        </p>
        <p>
          <Link href="/login">Se connecter</Link> pour acceder a l&apos;espace prive.
        </p>
      </section>
    </main>
  );
}
