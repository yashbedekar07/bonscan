-- =====================================================================
-- BonScan database schema
-- Run this whole file in the Supabase SQL Editor (Dashboard → SQL Editor → New query).
-- It is safe to run more than once.
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. Tables
-- ---------------------------------------------------------------------

-- Spending categories, shared by all users (seeded below).
create table if not exists public.categories (
    id   integer generated always as identity primary key,
    name text not null unique,
    icon text
);

-- One row per scanned receipt.
create table if not exists public.receipts (
    id             uuid primary key default gen_random_uuid(),
    user_id        uuid not null references auth.users (id) on delete cascade,
    store_name     text,
    purchase_date  date,
    total_amount   numeric(10, 2),
    currency       text not null default 'EUR',
    vat_amount     numeric(10, 2),
    image_path     text,           -- path inside the "receipts" storage bucket
    raw_ai_json    jsonb,          -- untouched AI output, kept for debugging/re-processing
    created_at     timestamptz not null default now()
);

-- Line items on a receipt. Deleting a receipt deletes its items.
create table if not exists public.receipt_items (
    id           bigint generated always as identity primary key,
    receipt_id   uuid not null references public.receipts (id) on delete cascade,
    name         text not null,
    quantity     numeric(10, 3) not null default 1,
    unit_price   numeric(10, 2),
    total_price  numeric(10, 2) not null,
    category_id  integer references public.categories (id) on delete set null
);

-- Optional monthly spending limit per user and category.
create table if not exists public.budgets (
    id             bigint generated always as identity primary key,
    user_id        uuid not null references auth.users (id) on delete cascade,
    category_id    integer not null references public.categories (id) on delete cascade,
    monthly_limit  numeric(10, 2) not null check (monthly_limit > 0),
    unique (user_id, category_id)
);


-- ---------------------------------------------------------------------
-- 2. Indexes
-- ---------------------------------------------------------------------

create index if not exists receipts_user_date_idx  on public.receipts (user_id, purchase_date);
create index if not exists receipt_items_receipt_idx on public.receipt_items (receipt_id);


-- ---------------------------------------------------------------------
-- 3. Seed categories
-- ---------------------------------------------------------------------

insert into public.categories (name, icon) values
    ('Groceries',           '🛒'),
    ('Drugstore & Hygiene', '🧴'),
    ('Household',           '🧽'),
    ('Eating Out',          '🍽️'),
    ('Drinks & Snacks',     '🥤'),
    ('Transport',           '🚆'),
    ('Clothing',            '👕'),
    ('Electronics',         '🔌'),
    ('Deposit (Pfand)',     '♻️'),
    ('Other',               '📦')
on conflict (name) do nothing;


-- ---------------------------------------------------------------------
-- 4. Table permissions for logged-in users
--    (Row Level Security below decides WHICH rows they can touch.)
-- ---------------------------------------------------------------------

grant select on public.categories to authenticated;
grant select, insert, update, delete on public.receipts      to authenticated;
grant select, insert, update, delete on public.receipt_items to authenticated;
grant select, insert, update, delete on public.budgets       to authenticated;


-- ---------------------------------------------------------------------
-- 5. Row Level Security
--    (select auth.uid()) is the logged-in user's id. Wrapping it in a
--    sub-select lets Postgres evaluate it once per query instead of per row.
-- ---------------------------------------------------------------------

alter table public.categories    enable row level security;
alter table public.receipts      enable row level security;
alter table public.receipt_items enable row level security;
alter table public.budgets       enable row level security;

-- Categories: readable by any logged-in user, not writable.
drop policy if exists "Categories are readable by logged-in users" on public.categories;
create policy "Categories are readable by logged-in users"
    on public.categories for select
    to authenticated
    using (true);

-- Receipts: users can only see and change their own.
drop policy if exists "Users manage their own receipts" on public.receipts;
create policy "Users manage their own receipts"
    on public.receipts for all
    to authenticated
    using (user_id = (select auth.uid()))
    with check (user_id = (select auth.uid()));

-- Receipt items: allowed when the parent receipt belongs to the user.
drop policy if exists "Users manage items of their own receipts" on public.receipt_items;
create policy "Users manage items of their own receipts"
    on public.receipt_items for all
    to authenticated
    using (
        exists (
            select 1 from public.receipts r
            where r.id = receipt_id and r.user_id = (select auth.uid())
        )
    )
    with check (
        exists (
            select 1 from public.receipts r
            where r.id = receipt_id and r.user_id = (select auth.uid())
        )
    );

-- Budgets: users can only see and change their own.
drop policy if exists "Users manage their own budgets" on public.budgets;
create policy "Users manage their own budgets"
    on public.budgets for all
    to authenticated
    using (user_id = (select auth.uid()))
    with check (user_id = (select auth.uid()));


-- ---------------------------------------------------------------------
-- 6. Storage: private "receipts" bucket for receipt photos
--    Files must live under "<user id>/...", e.g. "3f2a.../2026-10-10-rewe.jpg".
-- ---------------------------------------------------------------------

insert into storage.buckets (id, name, public)
values ('receipts', 'receipts', false)
on conflict (id) do nothing;

drop policy if exists "Users upload receipts to their own folder" on storage.objects;
create policy "Users upload receipts to their own folder"
    on storage.objects for insert
    to authenticated
    with check (
        bucket_id = 'receipts'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );

drop policy if exists "Users read receipts in their own folder" on storage.objects;
create policy "Users read receipts in their own folder"
    on storage.objects for select
    to authenticated
    using (
        bucket_id = 'receipts'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );

-- Needed when a receipt (or a failed scan) is deleted: the backend removes the
-- photo while acting as the user, so the user must be allowed to delete it.
drop policy if exists "Users delete receipts in their own folder" on storage.objects;
create policy "Users delete receipts in their own folder"
    on storage.objects for delete
    to authenticated
    using (
        bucket_id = 'receipts'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );


-- ---------------------------------------------------------------------
-- 7. Daily scan limit (fair use of the Gemini quota)
--    One row per user per day with the number of AI scans.
--    Users may READ their own count but never change it directly; the only
--    way to count up is register_scan(), which checks the limit and adds 1
--    in a single locked step (two scans at once can't both slip through).
-- ---------------------------------------------------------------------

create table if not exists public.scan_usage (
    user_id  uuid not null references auth.users (id) on delete cascade,
    day      date not null,
    scans    integer not null default 0 check (scans >= 0),
    primary key (user_id, day)
);

alter table public.scan_usage enable row level security;
revoke all on public.scan_usage from anon, authenticated;
grant select on public.scan_usage to authenticated;

drop policy if exists "Users read their own scan usage" on public.scan_usage;
create policy "Users read their own scan usage"
    on public.scan_usage for select
    to authenticated
    using (user_id = (select auth.uid()));

-- Count one scan for the calling user if they're under daily_limit.
-- Returns allowed = false (and doesn't count) when the limit is reached.
-- "security definer" lets it write the table that users can't write directly;
-- it only ever touches the row of auth.uid(), so users can't affect each other.
create or replace function public.register_scan(daily_limit integer)
returns table (allowed boolean, used integer)
language plpgsql
security definer
set search_path = ''
as $$
declare
    uid uuid := auth.uid();
    today date := (now() at time zone 'Europe/Berlin')::date;
    current_scans integer;
begin
    if uid is null then
        raise exception 'Not authenticated';
    end if;

    insert into public.scan_usage (user_id, day, scans)
    values (uid, today, 0)
    on conflict (user_id, day) do nothing;

    -- Lock the row so parallel scans are counted one after another.
    select s.scans into current_scans
    from public.scan_usage s
    where s.user_id = uid and s.day = today
    for update;

    if current_scans >= daily_limit then
        return query select false, current_scans;
        return;
    end if;

    update public.scan_usage s
    set scans = s.scans + 1
    where s.user_id = uid and s.day = today
    returning s.scans into current_scans;

    return query select true, current_scans;
end;
$$;

revoke execute on function public.register_scan(integer) from public, anon;
grant execute on function public.register_scan(integer) to authenticated;
