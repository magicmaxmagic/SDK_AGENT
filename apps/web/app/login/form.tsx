"use client";

import { useActionState } from "react";

import { signInAction, signUpAction } from "./actions";

type ActionResult = { ok: boolean; message: string } | null;

export default function LoginForm() {
  const [signInState, signInFormAction, signInPending] = useActionState<ActionResult, FormData>(signInAction, null);
  const [signUpState, signUpFormAction, signUpPending] = useActionState<ActionResult, FormData>(signUpAction, null);

  return (
    <div className="card">
      <h2>Connexion</h2>
      <form action={signInFormAction}>
        <div className="form-row">
          <label htmlFor="email-in">Email</label>
          <input id="email-in" name="email" type="email" required />
        </div>
        <div className="form-row">
          <label htmlFor="password-in">Mot de passe</label>
          <input id="password-in" name="password" type="password" required minLength={6} />
        </div>
        <button disabled={signInPending} type="submit">
          {signInPending ? "Connexion..." : "Se connecter"}
        </button>
      </form>
      {signInState?.message ? <p>{signInState.message}</p> : null}

      <hr style={{ margin: "1.2rem 0", borderColor: "#e9dfd2" }} />

      <h2>Inscription</h2>
      <form action={signUpFormAction}>
        <div className="form-row">
          <label htmlFor="email-up">Email</label>
          <input id="email-up" name="email" type="email" required />
        </div>
        <div className="form-row">
          <label htmlFor="password-up">Mot de passe</label>
          <input id="password-up" name="password" type="password" required minLength={6} />
        </div>
        <button disabled={signUpPending} type="submit">
          {signUpPending ? "Creation..." : "Creer un compte"}
        </button>
      </form>
      {signUpState?.message ? <p>{signUpState.message}</p> : null}
    </div>
  );
}
