create table if not exists public.customers (
  id text primary key,
  customer_name text not null,
  level text not null,
  contact_name text not null,
  phone text not null,
  region text,
  status text not null,
  created_at text
);
