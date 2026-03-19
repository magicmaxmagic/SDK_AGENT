-- Notes table
create table if not exists public.notes (
  id bigint primary key generated always as identity,
  title text not null,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now()
);

alter table public.notes add column if not exists created_by uuid references auth.users(id);
alter table public.notes add column if not exists created_at timestamptz not null default now();

-- Sample data
insert into public.notes (title)
values
  ('Today I created a Supabase project.'),
  ('I added some data and queried it from Next.js.'),
  ('It was awesome!')
on conflict do nothing;

-- RLS
alter table public.notes enable row level security;

-- Read policy for authenticated users
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
