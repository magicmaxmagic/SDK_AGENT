"use client";

import { useActionState } from "react";

import { upsertSubscriptionAction, type DashboardActionResult } from "./actions";

type OrgOption = {
  id: string;
  name: string;
};

export default function SubscriptionForm({ organizations }: { organizations: OrgOption[] }) {
  const [state, formAction, pending] = useActionState<DashboardActionResult, FormData>(upsertSubscriptionAction, null);

  return (
    <form action={formAction} className="card">
      <h2>Subscription</h2>
      <div className="form-row">
        <label htmlFor="sub-org">Organisation</label>
        <select id="sub-org" name="organization_id" required disabled={organizations.length === 0}>
          <option value="">Choisir</option>
          {organizations.map((org) => (
            <option key={org.id} value={org.id}>
              {org.name}
            </option>
          ))}
        </select>
      </div>
      <div className="form-row">
        <label htmlFor="sub-plan">Plan</label>
        <select id="sub-plan" name="plan" defaultValue="free">
          <option value="free">free</option>
          <option value="pro">pro</option>
          <option value="team">team</option>
          <option value="enterprise">enterprise</option>
        </select>
      </div>
      <div className="form-row">
        <label htmlFor="sub-status">Status</label>
        <select id="sub-status" name="status" defaultValue="trialing">
          <option value="trialing">trialing</option>
          <option value="active">active</option>
          <option value="past_due">past_due</option>
          <option value="canceled">canceled</option>
        </select>
      </div>
      <div className="form-row">
        <label htmlFor="sub-seats">Sieges</label>
        <input id="sub-seats" name="seats" type="number" min={1} defaultValue={1} />
      </div>
      <button type="submit" disabled={pending || organizations.length === 0}>
        {pending ? "Mise a jour..." : "Mettre a jour"}
      </button>
      {organizations.length === 0 ? <p className="muted-label">Cree d abord une organisation.</p> : null}
      {state?.message ? <p className={state.ok ? "success-text" : "error-text"}>{state.message}</p> : null}
    </form>
  );
}
