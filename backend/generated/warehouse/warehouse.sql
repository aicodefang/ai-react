create table if not exists public.warehouses (
  id text primary key,
  warehouse_name text not null,
  warehouse_type text,
  manager_name text not null,
  phone text not null,
  city text,
  status text not null,
  created_at text
);
