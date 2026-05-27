create table if not exists public.suppliers (
  id text primary key,
  supplier_name text not null,
  supplier_type text not null,
  contact_name text not null,
  phone text not null,
  city text,
  cooperation_status text not null,
  created_at text
);
