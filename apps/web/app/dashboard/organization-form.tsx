"use client";

import { useActionState } from "react";

import { createOrganizationAction, type DashboardActionResult } from "./actions";

export default function OrganizationForm() {
  const [state, formAction, pending] = useActionState<DashboardActionResult, FormData>(createOrganizationAction, null);

  return (
    <form action={formAction} className="card">
      <h2>Nouvelle organisation</h2>
      <div className="form-row">
        <label htmlFor="org-name">Nom</label>
        <input id="org-name" name="name" type="text" required maxLength={120} placeholder="Acme Labs" />
      </div>
      <div className="form-row">
        <label htmlFor="org-slug">Slug (optionnel)</label>
        <input id="org-slug" name="slug" type="text" maxLength={60} placeholder="acme-labs" />
      </div>
      <button type="submit" disabled={pending}>{pending ? "Creation..." : "Creer l organisation"}</button>
      {state?.message ? <p className={state.ok ? "success-text" : "error-text"}>{state.message}</p> : null}
    </form>
  );
}
