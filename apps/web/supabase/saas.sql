-- Multi-tenant SaaS schema for organizations, projects, memberships, subscriptions

create extension if not exists pgcrypto;

create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now()
);

create table if not exists public.organization_memberships (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('owner', 'admin', 'member')),
  created_at timestamptz not null default now(),
  unique (organization_id, user_id)
);

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  name text not null,
  slug text not null,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  unique (organization_id, slug)
);

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null unique references public.organizations(id) on delete cascade,
  plan text not null check (plan in ('free', 'pro', 'team', 'enterprise')),
  status text not null check (status in ('trialing', 'active', 'past_due', 'canceled')),
  seats integer not null default 1 check (seats > 0),
  trial_ends_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.notes (
  id bigint primary key generated always as identity,
  title text not null,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now()
);

alter table public.organizations enable row level security;
alter table public.organization_memberships enable row level security;
alter table public.projects enable row level security;
alter table public.subscriptions enable row level security;
alter table public.notes enable row level security;

create policy if not exists "org_select_members"
on public.organizations
for select
to authenticated
using (
  exists (
    select 1
    from public.organization_memberships m
    where m.organization_id = organizations.id
      and m.user_id = auth.uid()
  )
);

create policy if not exists "org_insert_owner"
on public.organizations
for insert
to authenticated
with check (created_by = auth.uid());

create policy if not exists "membership_select_members"
on public.organization_memberships
for select
to authenticated
using (
  user_id = auth.uid()
  or exists (
    select 1
    from public.organization_memberships m
    where m.organization_id = organization_memberships.organization_id
      and m.user_id = auth.uid()
  )
);

create policy if not exists "membership_insert_self_owner"
on public.organization_memberships
for insert
to authenticated
with check (
  user_id = auth.uid()
  and (
    role = 'owner'
    or exists (
      select 1
      from public.organization_memberships m
      where m.organization_id = organization_memberships.organization_id
        and m.user_id = auth.uid()
        and m.role in ('owner', 'admin')
    )
  )
);

create policy if not exists "projects_select_members"
on public.projects
for select
to authenticated
using (
  exists (
    select 1
    from public.organization_memberships m
    where m.organization_id = projects.organization_id
      and m.user_id = auth.uid()
  )
);

create policy if not exists "projects_insert_admin"
on public.projects
for insert
to authenticated
with check (
  created_by = auth.uid()
  and exists (
    select 1
    from public.organization_memberships m
    where m.organization_id = projects.organization_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
);

create policy if not exists "subscriptions_select_members"
on public.subscriptions
for select
to authenticated
using (
  exists (
    select 1
    from public.organization_memberships m
    where m.organization_id = subscriptions.organization_id
      and m.user_id = auth.uid()
  )
);

create policy if not exists "subscriptions_insert_admin"
on public.subscriptions
for insert
to authenticated
with check (
  exists (
    select 1
    from public.organization_memberships m
    where m.organization_id = subscriptions.organization_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
);

create policy if not exists "subscriptions_update_admin"
on public.subscriptions
for update
to authenticated
using (
  exists (
    select 1
    from public.organization_memberships m
    where m.organization_id = subscriptions.organization_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
)
with check (
  exists (
    select 1
    from public.organization_memberships m
    where m.organization_id = subscriptions.organization_id
      and m.user_id = auth.uid()
      and m.role in ('owner', 'admin')
  )
);

create policy if not exists "notes_select_authenticated"
on public.notes
for select
to authenticated
using (true);

create policy if not exists "notes_insert_authenticated"
on public.notes
for insert
to authenticated
with check (created_by is null or created_by = auth.uid());

insert into public.notes (title)
values
  ('Today I created a Supabase project.'),
  ('I added some data and queried it from Next.js.'),
  ('It was awesome!')
on conflict do nothing;
