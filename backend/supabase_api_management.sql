create table if not exists public.api_definitions (
  id text primary key,
  name text not null,
  entity text not null,
  method text not null check (method in ('GET', 'POST', 'PUT', 'DELETE')),
  path text not null,
  action text not null check (action in ('list', 'create', 'update', 'delete')),
  request_schema jsonb not null default '[]'::jsonb,
  response_schema jsonb not null default '[]'::jsonb,
  mock_data jsonb null,
  status text not null check (status in ('draft', 'published')),
  created_at text not null
);

create index if not exists idx_api_definitions_entity on public.api_definitions(entity);
create index if not exists idx_api_definitions_action on public.api_definitions(action);

create table if not exists public.page_api_bindings (
  page_id text primary key references public.pages(id) on delete cascade,
  list_api_id text null references public.api_definitions(id) on delete set null,
  create_api_id text null references public.api_definitions(id) on delete set null,
  update_api_id text null references public.api_definitions(id) on delete set null,
  delete_api_id text null references public.api_definitions(id) on delete set null,
  updated_at text not null
);

create table if not exists public.customers (
  id text primary key,
  customer_name text not null,
  level text not null check (level in ('A', 'B', 'C')),
  contact_name text not null,
  phone text not null,
  region text not null,
  status text not null check (status in ('active', 'pending', 'disabled')),
  created_at text not null
);

create index if not exists idx_customers_customer_name on public.customers(customer_name);
create index if not exists idx_customers_level on public.customers(level);
create index if not exists idx_customers_status on public.customers(status);

create table if not exists public.workflow_runs (
  id text primary key,
  prompt text not null,
  status text not null check (status in ('pending', 'running', 'succeeded', 'failed')),
  shared_contract_json jsonb null,
  created_at text not null,
  updated_at text not null
);

create table if not exists public.workflow_steps (
  id text primary key,
  run_id text not null references public.workflow_runs(id) on delete cascade,
  agent_name text not null,
  status text not null check (status in ('pending', 'running', 'succeeded', 'failed')),
  summary text not null,
  output_json jsonb null,
  error_message text null,
  started_at text not null,
  finished_at text null
);

create table if not exists public.workflow_artifacts (
  id text primary key,
  run_id text not null references public.workflow_runs(id) on delete cascade,
  agent_name text not null,
  artifact_type text not null,
  target_path text not null,
  content_preview text not null,
  created_at text not null
);

create index if not exists idx_workflow_steps_run_id on public.workflow_steps(run_id);
create index if not exists idx_workflow_steps_agent_status on public.workflow_steps(agent_name, status);
create index if not exists idx_workflow_artifacts_run_id on public.workflow_artifacts(run_id);
