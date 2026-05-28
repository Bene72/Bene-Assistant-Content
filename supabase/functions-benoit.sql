-- ============================================
-- FONCTIONS SQL SUPABASE — BENOIT COACH
-- Exécuter dans Supabase SQL Editor
-- APRÈS le schema.sql principal
-- ============================================

-- ─────────────────────────────────────────────
-- 1. Fonction : clients à relancer
--    Appelée par n8n toutes les heures
--    Retourne tous les clients qui ont besoin
--    d'un rappel selon leur situation
-- ─────────────────────────────────────────────
create or replace function get_clients_to_remind(p_org_id uuid)
returns table (
  client_email    text,
  client_name     text,
  client_goal     text,
  reminder_type   text,
  seance_date     text,
  seance_heure    text,
  last_seance_date text,
  days_inactive   int,
  days_remaining  int,
  sessions_remaining int,
  calendar_link   text
)
language plpgsql
as $$
begin

  -- ── RAPPEL SÉANCE J-1 ──────────────────────
  -- Leads avec une tâche "séance" prévue demain
  return query
  select
    l.email,
    l.full_name,
    coalesce(l.pain_points->0, '"objectif fitness"')::text,
    'seance_demain'::text,
    to_char(t.due_date, 'DD/MM/YYYY'),
    to_char(t.due_date, 'HH24h:MI'),
    null::text,
    null::int,
    null::int,
    null::int,
    'https://calendly.com/benoit-coach'
  from tasks t
  join leads l on l.email = (t.metadata->>'client_email')
  where t.org_id = p_org_id
    and t.status = 'todo'
    and t.title ilike '%séance%'
    and t.due_date::date = current_date + interval '1 day'
    and not exists (
      select 1 from events e
      where e.org_id = p_org_id
        and e.type = 'reminder.seance_demain'
        and (e.data->>'client_email') = l.email
        and e.created_at > now() - interval '20 hours'
    );

  -- ── CHECK-IN J+3 ───────────────────────────
  -- Clients dont la dernière séance était il y a ~3 jours
  return query
  select
    l.email,
    l.full_name,
    coalesce(l.pain_points->0, '"objectif fitness"')::text,
    'checkin_post_seance'::text,
    null::text,
    null::text,
    to_char(t.completed_at, 'DD/MM/YYYY'),
    null::int,
    null::int,
    null::int,
    'https://calendly.com/benoit-coach'
  from tasks t
  join leads l on l.email = (t.metadata->>'client_email')
  where t.org_id = p_org_id
    and t.status = 'done'
    and t.title ilike '%séance%'
    and t.completed_at::date = current_date - interval '3 days'
    and not exists (
      select 1 from events e
      where e.org_id = p_org_id
        and e.type = 'reminder.checkin_j3'
        and (e.data->>'client_email') = l.email
        and e.created_at > now() - interval '4 days'
    );

  -- ── CLIENT INACTIF +14 JOURS ───────────────
  return query
  select
    l.email,
    l.full_name,
    coalesce(l.pain_points->0, '"objectif fitness"')::text,
    'client_inactif'::text,
    null::text,
    null::text,
    to_char(l.last_contact_at, 'DD/MM/YYYY'),
    extract(day from now() - l.last_contact_at)::int,
    null::int,
    null::int,
    'https://calendly.com/benoit-coach'
  from leads l
  where l.org_id = p_org_id
    and l.stage in ('qualified', 'won')
    and l.last_contact_at < now() - interval '14 days'
    and not exists (
      select 1 from events e
      where e.org_id = p_org_id
        and e.type = 'reminder.inactif'
        and (e.data->>'client_email') = l.email
        and e.created_at > now() - interval '7 days'
    );

  -- ── FIN DE PACK DANS 7 JOURS ──────────────
  -- Leads avec metadata pack_sessions_total et pack_sessions_used
  return query
  select
    l.email,
    l.full_name,
    coalesce(l.pain_points->0, '"objectif fitness"')::text,
    'fin_de_pack'::text,
    null::text,
    null::text,
    null::text,
    null::int,
    7,
    (
      (l.enriched_data->>'pack_sessions_total')::int
      - (l.enriched_data->>'pack_sessions_used')::int
    ),
    'https://calendly.com/benoit-coach'
  from leads l
  where l.org_id = p_org_id
    and l.stage = 'won'
    and (l.enriched_data->>'pack_sessions_total') is not null
    and (
      (l.enriched_data->>'pack_sessions_total')::int
      - (l.enriched_data->>'pack_sessions_used')::int
    ) <= 2
    and not exists (
      select 1 from events e
      where e.org_id = p_org_id
        and e.type = 'reminder.fin_pack'
        and (e.data->>'client_email') = l.email
        and e.created_at > now() - interval '14 days'
    );

end;
$$;

-- ─────────────────────────────────────────────
-- 2. Fonction : incrémenter stats agent
-- ─────────────────────────────────────────────
create or replace function increment_agent_stats(
  p_agent_id uuid,
  p_messages int default 0,
  p_tasks int default 0
)
returns void
language plpgsql
as $$
begin
  update agents
  set
    messages_count   = messages_count + p_messages,
    tasks_completed  = tasks_completed + p_tasks,
    last_active_at   = now()
  where id = p_agent_id;
end;
$$;

-- ─────────────────────────────────────────────
-- 3. Vue : récap hebdo pour Benoit
-- ─────────────────────────────────────────────
create or replace view weekly_recap as
select
  o.name as org_name,
  count(distinct l.id) filter (where l.created_at > now() - interval '7 days') as new_leads_week,
  count(distinct l.id) filter (where l.stage = 'won') as total_clients_actifs,
  count(t.id) filter (where t.status = 'done' and t.updated_at > now() - interval '7 days') as tasks_done_week,
  count(t.id) filter (where t.status = 'blocked') as tasks_blocked,
  count(c.id) filter (where c.status = 'open') as conversations_ouvertes,
  count(c.id) filter (where c.status = 'escalated') as escalades_en_cours
from organisations o
left join leads l on l.org_id = o.id
left join tasks t on t.org_id = o.id
left join conversations c on c.org_id = o.id
group by o.id, o.name;

-- ─────────────────────────────────────────────
-- 4. Trigger : log automatique quand un lead
--    passe en stage "won" (client signé)
-- ─────────────────────────────────────────────
create or replace function on_lead_won()
returns trigger as $$
begin
  if new.stage = 'won' and old.stage != 'won' then
    -- Créer les tâches d'onboarding automatiquement
    insert into tasks (org_id, title, priority, status, auto_generated, generation_context, due_date)
    values
      (new.org_id, 'Créer fiche client — ' || new.full_name, 'urgent', 'todo', true, 'Lead won auto', now() + interval '1 day'),
      (new.org_id, 'Envoyer questionnaire initial — ' || new.full_name, 'high', 'todo', true, 'Lead won auto', now() + interval '1 day'),
      (new.org_id, 'Planifier séance bilan — ' || new.full_name, 'high', 'todo', true, 'Lead won auto', now() + interval '3 days'),
      (new.org_id, 'Créer programme semaines 1-2 — ' || new.full_name, 'medium', 'todo', true, 'Lead won auto', now() + interval '5 days');

    -- Log event
    insert into events (org_id, type, source, data)
    values (new.org_id, 'lead.won', 'trigger', json_build_object('lead_id', new.id, 'name', new.full_name, 'email', new.email));
  end if;
  return new;
end;
$$ language plpgsql;

create trigger t_lead_won
  after update on leads
  for each row
  execute function on_lead_won();
