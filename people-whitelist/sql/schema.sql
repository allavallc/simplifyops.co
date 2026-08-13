-- Core schema for the people whitelist app

create table if not exists people (
  id serial primary key,
  person_name text,
  person_email text unique not null,
  telegram_id text unique,
  telegram_username text,
  telegram_first_name text,
  telegram_last_name text,
  telegram_last_seen_at timestamptz,
  phone_country_code text,
  phone_number text,
  admin boolean not null default false,
  authority text not null default 'member',
  can_converse boolean not null default true,
  can_influence boolean not null default true,
  status text not null default 'allowed',
  notes text,
  created_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists contact_requests (
  id serial primary key,
  request_id text,
  channel text not null,
  from_id text not null,
  from_name text,
  chat_id text not null,
  message_text text not null,
  raw jsonb,
  status text not null default 'pending',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  reviewed_at timestamptz,
  reviewed_by text
);

create unique index if not exists contact_requests_request_id_key on contact_requests (request_id);

create table if not exists audit_log (
  id serial primary key,
  actor_email text,
  action text not null,
  subject_email text,
  old_value jsonb,
  new_value jsonb,
  created_at timestamptz not null default now()
);

create table if not exists sessions (
  sid varchar not null primary key,
  sess json not null,
  expire timestamp(6) not null
);
