# Copilot Instructions for SDK_AGENT

Use these rules when proposing changes in this repository.

## Goals
- Keep Python SDK behavior stable and policy-first.
- Keep the web app in `apps/web` deployable on Vercel.
- Prefer minimal patches over large refactors.

## Required Quality Checks
- For Python changes: run `pytest -q` from repo root.
- For web changes: run `npm run lint` and `npm run build` in `apps/web`.
- When touching auth paths, include at least one regression test or route-level validation.

## CI/CD Expectations
- Do not bypass GitHub Actions checks.
- Keep `.github/workflows/ci-cd.yml` green before merge.
- Production deployment is done by GitHub Actions to Vercel on pushes to `main`.

## Auth and Security
- Never hardcode secrets.
- Use Supabase env variables only:
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- Keep `/dashboard` and `/api/private` protected.

## Change Style
- Preserve existing APIs unless explicitly requested.
- Add short, meaningful comments only where logic is non-obvious.
- Prefer ASCII-only content unless file already uses Unicode.
