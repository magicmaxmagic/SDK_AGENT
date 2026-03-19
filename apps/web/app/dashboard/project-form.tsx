"use client";

import { useActionState } from "react";

import { createProjectAction, type DashboardActionResult } from "./actions";

type OrgOption = {
  id: string;
  name: string;
};

export default function ProjectForm({ organizations }: { organizations: OrgOption[] }) {
  const [state, formAction, pending] = useActionState<DashboardActionResult, FormData>(createProjectAction, null);

  return (
    <form action={formAction} className="card">
      <h2>Nouveau projet</h2>
      <div className="form-row">
        <label htmlFor="project-org">Organisation</label>
        <select id="project-org" name="organization_id" required disabled={organizations.length === 0}>
          <option value="">Choisir</option>
          {organizations.map((org) => (
            <option key={org.id} value={org.id}>
              {org.name}
            </option>
          ))}
        </select>
      </div>
      <div className="form-row">
        <label htmlFor="project-name">Nom</label>
        <input id="project-name" name="name" type="text" required maxLength={120} placeholder="SDK Platform" />
      </div>
      <div className="form-row">
        <label htmlFor="project-slug">Slug (optionnel)</label>
        <input id="project-slug" name="slug" type="text" maxLength={60} placeholder="sdk-platform" />
      </div>
      <button type="submit" disabled={pending || organizations.length === 0}>
        {pending ? "Creation..." : "Creer le projet"}
      </button>
      {organizations.length === 0 ? <p className="muted-label">Cree d abord une organisation.</p> : null}
      {state?.message ? <p className={state.ok ? "success-text" : "error-text"}>{state.message}</p> : null}
    </form>
  );
}
