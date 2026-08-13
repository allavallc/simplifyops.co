export async function initDb(pool) {
  await pool.query(`
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
      status text not null default 'allowed',
      notes text,
      created_by text,
      created_at timestamptz not null default now(),
      updated_at timestamptz not null default now()
    );
  `);

  await pool.query(`
    create table if not exists audit_log (
      id serial primary key,
      actor_email text,
      action text not null,
      subject_email text,
      old_value jsonb,
      new_value jsonb,
      created_at timestamptz not null default now()
    );
  `);

  await pool.query(`
    create table if not exists job_preferences (
      id serial primary key,
      person_email text not null references people(person_email) on delete cascade unique,
      keywords text[] not null default '{}',
      min_budget integer,
      job_type text not null default 'any',
      remote_only boolean not null default true,
      no_agencies boolean not null default true,
      extra_instructions text,
      updated_at timestamptz not null default now()
    );
  `);

  await pool.query(`
    alter table if exists people
      add column if not exists cv_filename text,
      add column if not exists cv_path text,
      add column if not exists cv_uploaded_at timestamptz;
  `);

  await pool.query(`
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

    alter table if exists contact_requests
      add column if not exists request_id text;
  `);

  await pool.query(`
    create unique index if not exists contact_requests_request_id_key on contact_requests (request_id);
  `);

  await pool.query(`
    create table if not exists google_tokens (
      id serial primary key,
      person_email text not null references people(person_email) on delete cascade,
      access_token text,
      refresh_token text,
      token_expiry timestamptz,
      scopes text[] not null default '{}',
      created_at timestamptz not null default now(),
      updated_at timestamptz not null default now(),
      unique (person_email)
    );
  `);

  await pool.query(`
    create table if not exists sessions (
      sid varchar not null primary key,
      sess json not null,
      expire timestamp(6) not null
    );
  `);

  await pool.query(`
    alter table if exists people
      add column if not exists telegram_id text;

    alter table if exists people
      add column if not exists telegram_username text;

    alter table if exists people
      add column if not exists telegram_first_name text;

    alter table if exists people
      add column if not exists telegram_last_name text;

    alter table if exists people
      add column if not exists telegram_last_seen_at timestamptz;

    alter table if exists people
      add column if not exists phone_country_code text;

    alter table if exists people
      add column if not exists phone_number text;

    alter table if exists people
      add column if not exists admin boolean not null default false;

    alter table if exists people
      add column if not exists status text not null default 'allowed';

    alter table if exists people
      add column if not exists notes text;

    alter table if exists people
      add column if not exists created_by text;

    alter table if exists people
      add column if not exists person_name text;

    alter table if exists people
      add column if not exists created_at timestamptz not null default now();

    alter table if exists people
      add column if not exists updated_at timestamptz not null default now();

    create unique index if not exists people_telegram_id_key on people (telegram_id);
  `);

  await pool.query(`
    do $$
    begin
      if exists (
        select 1
        from information_schema.tables
        where table_schema = 'public' and table_name = 'whitelist_entries'
      ) and not exists (
        select 1
        from information_schema.tables
        where table_schema = 'public' and table_name = 'people'
      ) then
        alter table whitelist_entries rename to people;
      end if;

      if exists (
        select 1
        from information_schema.tables
        where table_schema = 'public' and table_name = 'admins'
      ) then
        if exists (
          select 1 from information_schema.columns
          where table_schema = 'public' and table_name = 'people' and column_name = 'email'
        ) then
          alter table people rename column email to person_email;
        end if;

        if exists (
          select 1 from information_schema.columns
          where table_schema = 'public' and table_name = 'people' and column_name = 'name'
        ) then
          alter table people rename column name to person_name;
        end if;

        if exists (
          select 1 from information_schema.columns
          where table_schema = 'public' and table_name = 'people' and column_name = 'active'
        ) then
          alter table people rename column active to admin;
        end if;

        update people set admin = coalesce(admin, false);

        insert into people (person_name, person_email, telegram_id, telegram_username, telegram_first_name, telegram_last_name, telegram_last_seen_at, phone_country_code, phone_number, admin, status, notes, created_by, created_at)
        select name, email, null, null, null, null, null, null, null, true, 'allowed', null, null, created_at
        from admins
        on conflict (person_email) do update
        set admin = excluded.admin;

        drop table admins;
      end if;
    exception
      when duplicate_column then
        null;
      when undefined_table then
        null;
    end $$;
  `);
}
