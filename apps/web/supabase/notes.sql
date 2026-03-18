-- Notes table
create table if not exists public.notes (
  id bigint primary key generated always as identity,
  title text not null
);

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
