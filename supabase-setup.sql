-- À coller dans Supabase > SQL Editor > New Query
-- puis cliquer sur "Run"

create table contacts (
  id uuid default gen_random_uuid() primary key,
  name text not null,
  email text not null,
  phone text,
  service text,
  message text not null,
  created_at timestamptz default now()
);

-- Autoriser les insertions publiques (formulaire de contact)
alter table contacts enable row level security;

create policy "Allow public insert"
  on contacts
  for insert
  to anon
  with check (true);

-- Seul toi (connecté) peux lire les messages
create policy "Allow authenticated read"
  on contacts
  for select
  to authenticated
  using (true);
