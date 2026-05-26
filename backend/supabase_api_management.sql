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
