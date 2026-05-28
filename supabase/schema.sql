-- ============================================
-- AUTOFLOW — SCHÉMA SUPABASE COMPLET
-- ============================================
-- Exécuter dans Supabase SQL Editor

-- Extensions
create extension if not exists "uuid-ossp";
create extension if not exists "pg_cron";

-- ============================================
-- 1. ORGANISATIONS (clients PME)
-- ============================================
create table organisations (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  slug text unique not null,
  plan text not null default 'starter' check (plan in ('starter','pro','enterprise')),
  email text not null,
  phone text,
  website text,
  -- Limites par plan
  max_automations int default 5,
  max_agents int default 1,
  -- Metadata
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ============================================
-- 2. UTILISATEURS
-- ============================================
create table users (
  id uuid primary key references auth.users(id) on delete cascade,
  org_id uuid references organisations(id) on delete cascade,
  email text not null,
  full_name text,
  role text not null default 'member' check (role in ('owner','admin','member')),
  avatar_url text,
  created_at timestamptz default now()
);

-- ============================================
-- 3. AGENTS IA
-- ============================================
create table agents (
  id uuid primary key default uuid_generate_v4(),
  org_id uuid references organisations(id) on delete cascade,
  name text not null,
  type text not null check (type in ('communication','commercial','realisation','reporting')),
  status text not null default 'active' check (status in ('active','paused','error')),
  -- Configuration
  system_prompt text not null,
  model text default 'claude-sonnet-4-20250514',
  temperature float default 0.3,
  -- Intégrations
  channels jsonb default '[]', -- [{type: "email", config: {...}}, {type: "slack", ...}]
  tools jsonb default '[]',    -- outils autorisés
  -- Stats
  messages_count int default 0,
  tasks_completed int default 0,
  last_active_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ============================================
-- 4. CONVERSATIONS (agent communication)
-- ============================================
create table conversations (
  id uuid primary key default uuid_generate_v4(),
  org_id uuid references organisations(id) on delete cascade,
  agent_id uuid references agents(id),
  -- Contact externe
  contact_email text,
  contact_name text,
  contact_phone text,
  -- Statut
  status text default 'open' check (status in ('open','handled','closed','escalated')),
  channel text not null check (channel in ('email','slack','whatsapp','widget')),
  subject text,
  -- Escalade
  assigned_to uuid references users(id),
  escalated_at timestamptz,
  escalation_reason text,
  -- Stats
  message_count int default 0,
  sentiment text check (sentiment in ('positive','neutral','negative')),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table messages (
  id uuid primary key default uuid_generate_v4(),
  conversation_id uuid references conversations(id) on delete cascade,
  role text not null check (role in ('user','assistant','system')),
  content text not null,
  metadata jsonb default '{}',
  created_at timestamptz default now()
);

-- ============================================
-- 5. LEADS (agent commercial)
-- ============================================
create table leads (
  id uuid primary key default uuid_generate_v4(),
  org_id uuid references organisations(id) on delete cascade,
  agent_id uuid references agents(id),
  -- Info contact
  email text not null,
  full_name text,
  company text,
  phone text,
  -- Qualification
  score int default 0 check (score between 0 and 100),
  stage text default 'new' check (stage in ('new','contacted','qualified','proposal','won','lost')),
  source text, -- formulaire, email, linkedin...
  budget_range text,
  timeline text,
  pain_points jsonb default '[]',
  -- Suivi
  last_contact_at timestamptz,
  next_action text,
  next_action_at timestamptz,
  assigned_to uuid references users(id),
  notes text,
  -- Données enrichissement
  enriched_data jsonb default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table lead_activities (
  id uuid primary key default uuid_generate_v4(),
  lead_id uuid references leads(id) on delete cascade,
  type text not null, -- email_sent, call_logged, score_updated, stage_changed
  description text,
  metadata jsonb default '{}',
  created_by uuid references users(id),
  created_at timestamptz default now()
);

-- ============================================
-- 6. PROJETS & TÂCHES (agent réalisation)
-- ============================================
create table projects (
  id uuid primary key default uuid_generate_v4(),
  org_id uuid references organisations(id) on delete cascade,
  lead_id uuid references leads(id),
  name text not null,
  description text,
  status text default 'active' check (status in ('draft','active','on_hold','completed','cancelled')),
  priority text default 'medium' check (priority in ('low','medium','high','urgent')),
  -- Dates
  start_date date,
  due_date date,
  completed_at timestamptz,
  -- Budget
  budget_euros int,
  spent_euros int default 0,
  -- Stats
  tasks_total int default 0,
  tasks_done int default 0,
  progress int default 0 check (progress between 0 and 100),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table tasks (
  id uuid primary key default uuid_generate_v4(),
  project_id uuid references projects(id) on delete cascade,
  org_id uuid references organisations(id) on delete cascade,
  title text not null,
  description text,
  status text default 'todo' check (status in ('todo','in_progress','review','done','blocked')),
  priority text default 'medium' check (priority in ('low','medium','high','urgent')),
  -- Assignation
  assigned_to uuid references users(id),
  assigned_by_agent uuid references agents(id),
  -- Dates
  due_date timestamptz,
  completed_at timestamptz,
  estimated_hours float,
  actual_hours float,
  -- Auto-génération
  auto_generated boolean default false,
  generation_context text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ============================================
-- 7. AUTOMATIONS / WORKFLOWS
-- ============================================
create table automations (
  id uuid primary key default uuid_generate_v4(),
  org_id uuid references organisations(id) on delete cascade,
  name text not null,
  description text,
  status text default 'active' check (status in ('active','paused','error','draft')),
  -- Source (n8n, make, zapier, natif)
  platform text not null check (platform in ('n8n','make','zapier','native')),
  external_id text, -- ID du workflow dans n8n/Make/Zapier
  webhook_url text,
  -- Config
  trigger_type text, -- webhook, schedule, email, etc.
  trigger_config jsonb default '{}',
  -- Stats
  runs_total int default 0,
  runs_success int default 0,
  runs_error int default 0,
  last_run_at timestamptz,
  last_run_status text,
  avg_duration_ms int,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table automation_logs (
  id uuid primary key default uuid_generate_v4(),
  automation_id uuid references automations(id) on delete cascade,
  status text not null check (status in ('success','error','running')),
  duration_ms int,
  input_data jsonb,
  output_data jsonb,
  error_message text,
  created_at timestamptz default now()
);

-- ============================================
-- 8. EVENTS (journal global)
-- ============================================
create table events (
  id uuid primary key default uuid_generate_v4(),
  org_id uuid references organisations(id) on delete cascade,
  type text not null, -- agent.message, lead.qualified, task.created, automation.run...
  source text,        -- agent_id, automation_id, user_id
  data jsonb default '{}',
  created_at timestamptz default now()
);

-- ============================================
-- INDEXES
-- ============================================
create index idx_agents_org on agents(org_id);
create index idx_conversations_org on conversations(org_id);
create index idx_messages_conv on messages(conversation_id);
create index idx_leads_org on leads(org_id);
create index idx_leads_score on leads(score desc);
create index idx_tasks_project on tasks(project_id);
create index idx_tasks_assigned on tasks(assigned_to);
create index idx_automation_logs_auto on automation_logs(automation_id, created_at desc);
create index idx_events_org_type on events(org_id, type, created_at desc);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================
alter table organisations enable row level security;
alter table agents enable row level security;
alter table conversations enable row level security;
alter table messages enable row level security;
alter table leads enable row level security;
alter table projects enable row level security;
alter table tasks enable row level security;
alter table automations enable row level security;

-- Policy : chaque user ne voit que son org
create policy "org_isolation" on agents
  using (org_id = (select org_id from users where id = auth.uid()));

create policy "org_isolation" on conversations
  using (org_id = (select org_id from users where id = auth.uid()));

create policy "org_isolation" on leads
  using (org_id = (select org_id from users where id = auth.uid()));

create policy "org_isolation" on projects
  using (org_id = (select org_id from users where id = auth.uid()));

create policy "org_isolation" on tasks
  using (org_id = (select org_id from users where id = auth.uid()));

create policy "org_isolation" on automations
  using (org_id = (select org_id from users where id = auth.uid()));

-- ============================================
-- TRIGGERS updated_at
-- ============================================
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger t_organisations before update on organisations for each row execute function update_updated_at();
create trigger t_agents before update on agents for each row execute function update_updated_at();
create trigger t_conversations before update on conversations for each row execute function update_updated_at();
create trigger t_leads before update on leads for each row execute function update_updated_at();
create trigger t_projects before update on projects for each row execute function update_updated_at();
create trigger t_tasks before update on tasks for each row execute function update_updated_at();
create trigger t_automations before update on automations for each row execute function update_updated_at();
