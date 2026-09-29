-- Run this once in the Supabase SQL editor.
create table if not exists public.datasets (
  id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  filename text not null,
  storage_path text not null unique,
  content_type text not null default 'application/octet-stream',
  row_count integer not null,
  column_count integer not null,
  column_names jsonb not null default '[]'::jsonb,
  preview jsonb not null default '[]'::jsonb,
  profile jsonb not null default '[]'::jsonb,
  status text not null default 'ready' check (status in ('processing', 'ready', 'failed')),
  error_message text,
  created_at timestamptz not null default now()
);

alter table public.datasets enable row level security;

grant select, insert, update on public.datasets to authenticated;

drop policy if exists "Users can read their own datasets" on public.datasets;
drop policy if exists "Users can insert their own datasets" on public.datasets;
drop policy if exists "Users can update their own datasets" on public.datasets;

create policy "Users can read their own datasets"
  on public.datasets for select using (auth.uid() = user_id);

create policy "Users can insert their own datasets"
  on public.datasets for insert with check (auth.uid() = user_id);

create policy "Users can update their own datasets"
  on public.datasets for update using (auth.uid() = user_id);

insert into storage.buckets (id, name, public)
values ('datasets', 'datasets', false)
on conflict (id) do nothing;

drop policy if exists "Users can access their dataset files" on storage.objects;
drop policy if exists "Users can upload their own dataset files" on storage.objects;
drop policy if exists "Users can read their own dataset files" on storage.objects;

create policy "Users can upload their own dataset files"
  on storage.objects for insert to authenticated
  with check (
    bucket_id = 'datasets'
    and (storage.foldername(name))[1] = (select auth.jwt()->>'sub')
  );

create policy "Users can read their own dataset files"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'datasets'
    and (storage.foldername(name))[1] = (select auth.jwt()->>'sub')
  );
