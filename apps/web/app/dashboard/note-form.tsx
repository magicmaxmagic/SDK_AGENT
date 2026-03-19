"use client";

import { useActionState } from "react";

import { createNoteAction, type DashboardActionResult } from "./actions";

export default function NoteForm() {
  const [state, formAction, pending] = useActionState<DashboardActionResult, FormData>(createNoteAction, null);

  return (
    <form action={formAction} className="note-form card">
      <h2>Ajouter une note</h2>
      <div className="form-row">
        <label htmlFor="note-title">Titre</label>
        <input id="note-title" name="title" type="text" required maxLength={200} placeholder="Ex: Deploy staging valide" />
      </div>
      <button type="submit" disabled={pending}>{pending ? "Ajout..." : "Ajouter"}</button>
      {state?.message ? <p className={state.ok ? "success-text" : "error-text"}>{state.message}</p> : null}
    </form>
  );
}
