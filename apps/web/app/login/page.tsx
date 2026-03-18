import Link from "next/link";

import LoginForm from "./form";

export default function LoginPage() {
  return (
    <main>
      <div className="header">
        <h1>Authentification</h1>
        <Link href="/">Accueil</Link>
      </div>
      <LoginForm />
    </main>
  );
}
