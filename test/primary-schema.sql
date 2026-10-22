-- First persistent CloudBase -> PostgreSQL table. Run in levelread_prod after
-- confirming that public.enil_news does not already exist. This migration
-- creates structure only; loading and read cutover are separate operations.
CREATE TABLE public.enil_news (
  _id text PRIMARY KEY,
  titleid text,
  title text,
  summary text,
  date_ms bigint,
  original_url text,
  cover text,
  is_public boolean,
  read_count bigint,
  levels jsonb,
  updated_at_ms bigint,
  source_extra jsonb NOT NULL DEFAULT '{}'::jsonb,
  imported_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX enil_news_public_date_id_idx
  ON public.enil_news (is_public, date_ms DESC, _id);
CREATE INDEX enil_news_titleid_idx
  ON public.enil_news (titleid);

CREATE TABLE public.enil_runtime_config (
  _id text PRIMARY KEY,
  config_key text NOT NULL,
  enabled boolean,
  auth_mode_default text,
  auth_mode_rules jsonb,
  state text,
  note text,
  internal_user_ids jsonb,
  updated_at timestamptz,
  updated_at_source jsonb NOT NULL,
  source_extra jsonb NOT NULL DEFAULT '{}'::jsonb,
  imported_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX enil_runtime_config_key_idx
  ON public.enil_runtime_config (config_key);

CREATE TABLE public.enli_news_title_translation (
  _id text PRIMARY KEY,
  news_id text NOT NULL,
  language_code text NOT NULL,
  title text NOT NULL,
  status text NOT NULL,
  provider text,
  version text,
  created_at_ms bigint NOT NULL,
  updated_at_ms bigint NOT NULL,
  source_extra jsonb NOT NULL DEFAULT '{}'::jsonb,
  imported_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX enli_news_title_translation_news_language_idx
  ON public.enli_news_title_translation (news_id, language_code);

CREATE TABLE public.enli_news_translation (
  _id text PRIMARY KEY,
  news_id text NOT NULL,
  language_code text NOT NULL,
  title text NOT NULL,
  summary text NOT NULL,
  levels jsonb NOT NULL,
  source_extra jsonb NOT NULL DEFAULT '{}'::jsonb,
  imported_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX enli_news_translation_news_language_idx
  ON public.enli_news_translation (news_id, language_code);

CREATE TABLE public.enil_word_tts (
  _id text PRIMARY KEY,
  hash_id text NOT NULL,
  file_path text NOT NULL,
  create_at_ms bigint NOT NULL,
  pronunciation_ipa text,
  pronunciation_version text,
  updated_at_ms bigint,
  source_extra jsonb NOT NULL DEFAULT '{}'::jsonb,
  imported_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX enil_word_tts_hash_id_idx
  ON public.enil_word_tts (hash_id);

CREATE TABLE public.enil_word_dictionary (
  _id text PRIMARY KEY,
  word text,
  language_code text,
  phonetic_us text,
  phonetic_uk text,
  parts json,
  updated_at_ms bigint,
  conversion_issues jsonb NOT NULL DEFAULT '[]'::jsonb,
  source_document json NOT NULL
);

CREATE INDEX enil_word_dictionary_lookup_idx
  ON public.enil_word_dictionary (word, language_code);

-- Generated from locally locked Better Auth 1.6.3 getSchema with expo, bearer, emailOTP.
-- Matches lib/auth/index.ts model names and additional fields.
-- Migration preparation: retain CloudBase _id and raw source; defer business
-- uniqueness, foreign keys, defaults and required-field constraints until audit.
-- The PG runtime adapter and data migration are separate work.

CREATE TABLE public.enil_auth_user (
  _id text PRIMARY KEY,
  id text,
  "name" text,
  "email" text,
  "emailVerified" boolean,
  "image" text,
  "createdAt" timestamptz,
  "updatedAt" timestamptz,
  "canonicalUserId" text,
  source_document jsonb NOT NULL
);
CREATE INDEX enil_auth_user_lookup_1_idx ON public.enil_auth_user ("id");
CREATE INDEX enil_auth_user_lookup_2_idx ON public.enil_auth_user ("email");
CREATE INDEX enil_auth_user_lookup_3_idx ON public.enil_auth_user ("canonicalUserId");

CREATE TABLE public.enil_auth_session (
  _id text PRIMARY KEY,
  id text,
  "expiresAt" timestamptz,
  "token" text,
  "createdAt" timestamptz,
  "updatedAt" timestamptz,
  "ipAddress" text,
  "userAgent" text,
  "userId" text,
  "authSource" text,
  source_document jsonb NOT NULL
);
CREATE INDEX enil_auth_session_lookup_1_idx ON public.enil_auth_session ("id");
CREATE INDEX enil_auth_session_lookup_2_idx ON public.enil_auth_session ("token");
CREATE INDEX enil_auth_session_lookup_3_idx ON public.enil_auth_session ("userId");
CREATE INDEX enil_auth_session_lookup_4_idx ON public.enil_auth_session ("expiresAt");

CREATE TABLE public.enil_auth_account (
  _id text PRIMARY KEY,
  id text,
  "accountId" text,
  "providerId" text,
  "userId" text,
  "accessToken" text,
  "refreshToken" text,
  "idToken" text,
  "accessTokenExpiresAt" timestamptz,
  "refreshTokenExpiresAt" timestamptz,
  "scope" text,
  "password" text,
  "createdAt" timestamptz,
  "updatedAt" timestamptz,
  source_document jsonb NOT NULL
);
CREATE INDEX enil_auth_account_lookup_1_idx ON public.enil_auth_account ("id");
CREATE INDEX enil_auth_account_lookup_2_idx ON public.enil_auth_account ("userId");
CREATE INDEX enil_auth_account_lookup_3_idx ON public.enil_auth_account ("providerId", "accountId");

CREATE TABLE public.enil_auth_verification (
  _id text PRIMARY KEY,
  id text,
  "identifier" text,
  "value" text,
  "expiresAt" timestamptz,
  "createdAt" timestamptz,
  "updatedAt" timestamptz,
  source_document jsonb NOT NULL
);
CREATE INDEX enil_auth_verification_lookup_1_idx ON public.enil_auth_verification ("id");
CREATE INDEX enil_auth_verification_lookup_2_idx ON public.enil_auth_verification ("identifier");

CREATE TABLE public.enil_user (
  _id text PRIMARY KEY,
  user_id text,
  language_code text,
  app_language_mode text,
  role text,
  level bigint,
  news_read bigint,
  words_read bigint,
  app_language_onboarding_version bigint,
  updated_at_ms bigint,
  minutes_read numeric,
  favorite_words_highlight_enabled boolean,
  subscription_email_notifications_enabled boolean,
  streak_day_list jsonb,
  subscription jsonb,
  subscription_by_env jsonb,
  clerk_data jsonb,
  data jsonb,
  source_document jsonb NOT NULL
);
CREATE INDEX enil_user_query_1_idx ON public.enil_user (user_id);
CREATE TABLE public.enil_vocabulary (
  _id text PRIMARY KEY,
  user_id text,
  news_id text,
  word text,
  explanation text,
  level_source jsonb,
  level_number bigint,
  created_at timestamptz,
  last_review_at timestamptz,
  mastered boolean,
  is_known boolean,
  review_count bigint,
  correct_count bigint,
  wrong_count bigint,
  updated_at_ms bigint,
  source_document jsonb NOT NULL
);
CREATE INDEX enil_vocabulary_query_1_idx ON public.enil_vocabulary (user_id, created_at DESC);
CREATE INDEX enil_vocabulary_query_2_idx ON public.enil_vocabulary (user_id, word);
CREATE TABLE public.enil_quiz_answer (
  _id text PRIMARY KEY,
  user_id text,
  news_id text,
  quiz_answer jsonb,
  updated_at_ms bigint,
  source_document jsonb NOT NULL
);
CREATE INDEX enil_quiz_answer_query_1_idx ON public.enil_quiz_answer (user_id, news_id);
CREATE TABLE public.enil_level_learning_progress (
  _id text PRIMARY KEY,
  user_id text,
  news_id text,
  level bigint,
  reading_completed_at_ms bigint,
  listening_completed_at_ms bigint,
  quiz_completed_at_ms bigint,
  completed_at_ms bigint,
  created_at_ms bigint,
  updated_at_ms bigint,
  source_document jsonb NOT NULL
);
CREATE INDEX enil_level_learning_progress_query_1_idx ON public.enil_level_learning_progress (user_id, news_id, level);
CREATE TABLE public.enil_news_favorite (
  _id text PRIMARY KEY,
  user_id text,
  news_id text,
  titleid text,
  level bigint,
  updated_at_ms bigint,
  created_at timestamptz,
  source_document jsonb NOT NULL
);
CREATE INDEX enil_news_favorite_query_1_idx ON public.enil_news_favorite (user_id, created_at DESC);
CREATE INDEX enil_news_favorite_query_2_idx ON public.enil_news_favorite (user_id, news_id);
CREATE TABLE public.enil_push_tokens (
  _id text PRIMARY KEY,
  user_id text,
  token text,
  created_at timestamptz,
  updated_at_ms bigint,
  source_document jsonb NOT NULL
);
CREATE INDEX enil_push_tokens_query_1_idx ON public.enil_push_tokens (token);
CREATE TABLE public.enil_auth_identity (
  _id text PRIMARY KEY,
  provider text,
  provider_user_id text,
  canonical_user_id text,
  email text,
  created_at timestamptz,
  updated_at timestamptz,
  source_document jsonb NOT NULL
);
CREATE INDEX enil_auth_identity_query_1_idx ON public.enil_auth_identity (provider, provider_user_id);
CREATE TABLE public.enil_subscription_events (
  _id text PRIMARY KEY,
  user_id text,
  provider text,
  event_id text,
  event_type text,
  transaction_id text,
  original_transaction_id text,
  product_id text,
  store text,
  environment text,
  currency text,
  event_timestamp_ms bigint,
  purchased_at_ms bigint,
  expires_at_ms bigint,
  created_at_ms bigint,
  updated_at_ms bigint,
  price numeric,
  raw_payload jsonb,
  source_document jsonb NOT NULL
);
CREATE INDEX enil_subscription_events_query_1_idx ON public.enil_subscription_events (provider, event_id);
CREATE INDEX enil_subscription_events_query_2_idx ON public.enil_subscription_events (user_id, event_timestamp_ms);
CREATE TABLE public.enil_waitlist (
  _id text PRIMARY KEY,
  email text,
  created_at timestamptz,
  source_document jsonb NOT NULL
);
CREATE INDEX enil_waitlist_query_1_idx ON public.enil_waitlist (email);
CREATE TABLE public.enil_event_log (
  _id text PRIMARY KEY,
  timestamp text,
  level text,
  service text,
  environment text,
  method text,
  path text,
  type text,
  source text,
  action text,
  outcome text,
  created_at timestamptz,
  actor jsonb,
  target jsonb,
  metadata jsonb,
  request jsonb,
  source_document jsonb NOT NULL
);
CREATE INDEX enil_event_log_query_1_idx ON public.enil_event_log (service, created_at DESC);
-- Structure for the disabled favorite-sync pilot. Apply separately before enabling.
-- This is NOT a full source change log or monotonic source version.
CREATE TABLE public.pg_sync_record_state (
  collection_name text NOT NULL,
  source_id text NOT NULL,
  deleted boolean NOT NULL,
  source_digest text,
  synced_at timestamptz NOT NULL,
  PRIMARY KEY (collection_name, source_id)
);

-- Apply before deploying direct-auth readers/writers. Activate only after all
-- authentication writers use the write guard and the old instances have drained.
BEGIN;
CREATE TABLE IF NOT EXISTS public.pg_auth_read_state (
  singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
  active boolean NOT NULL DEFAULT false
);
INSERT INTO public.pg_auth_read_state(singleton,active) VALUES (true,false)
ON CONFLICT (singleton) DO NOTHING;
CREATE TABLE IF NOT EXISTS public.pg_auth_read_pending (
  id uuid PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  sealed boolean NOT NULL DEFAULT false,
  refs jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(refs)='array')
);
CREATE INDEX IF NOT EXISTS pg_auth_read_pending_recovery_idx ON public.pg_auth_read_pending (created_at,id) WHERE sealed;
COMMIT;

-- Reviewed explicit migration; request handlers never apply DDL or activate authority.
BEGIN;
CREATE TABLE public.pg_primary_authority (
  singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
  authority text NOT NULL CHECK(authority IN ('cloudbase','postgresql')),
  changed_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO public.pg_primary_authority(singleton,authority) VALUES(true,'cloudbase');
ALTER TABLE public.enil_news ADD COLUMN source_document jsonb;
ALTER TABLE public.enil_runtime_config ADD COLUMN source_document jsonb;
ALTER TABLE public.enli_news_title_translation ADD COLUMN source_document jsonb;
ALTER TABLE public.enli_news_translation ADD COLUMN source_document jsonb;
ALTER TABLE public.enil_word_tts ADD COLUMN source_document jsonb;
CREATE TABLE public.enil_user_avatar (
  _id text PRIMARY KEY,
  user_id text NOT NULL,
  revision bigint NOT NULL CHECK(revision > 0),
  source_document jsonb NOT NULL
);
CREATE INDEX enil_user_avatar_user_id_idx ON public.enil_user_avatar(user_id);
-- Fence stale replicator images at the database boundary, including images that predate this migration.
CREATE FUNCTION public.pg_primary_require_writer() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (SELECT authority='postgresql' FROM public.pg_primary_authority WHERE singleton)
     AND current_setting('levelread.pg_primary',true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'PG primary rejects legacy source projection' USING ERRCODE='55000';
  END IF;
  RETURN NULL;
END $$;
DO $$ DECLARE table_name text; BEGIN
  FOREACH table_name IN ARRAY ARRAY['enil_news','enil_runtime_config','enli_news_title_translation','enli_news_translation',
    'enil_word_tts','enil_word_dictionary','enil_user','enil_vocabulary','enil_quiz_answer','enil_level_learning_progress',
    'enil_news_favorite','enil_push_tokens','enil_event_log','enil_auth_user','enil_auth_session',
    'enil_auth_account','enil_auth_verification','enil_auth_identity','enil_subscription_events','enil_user_avatar'] LOOP
    EXECUTE format('CREATE TRIGGER pg_primary_writer_fence BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE ON public.%I FOR EACH STATEMENT EXECUTE FUNCTION public.pg_primary_require_writer()',table_name);
  END LOOP;
END $$;
COMMIT;

-- Website is PG primary; explicitly allow existing guarded Admin/Google projections.
-- Default remains strict. Activation requires legacy_writers_enabled=true separately.
BEGIN;
ALTER TABLE public.pg_primary_authority ADD COLUMN legacy_writers_enabled boolean NOT NULL DEFAULT false;
CREATE TABLE public.pg_primary_owned_fields (
 collection_name text NOT NULL, source_id text NOT NULL,
 row_columns text[] NOT NULL DEFAULT '{}', document_fields text[] NOT NULL DEFAULT '{}', extra_fields text[] NOT NULL DEFAULT '{}',
 created_in_pg boolean NOT NULL DEFAULT false, deleted boolean NOT NULL DEFAULT false,
 PRIMARY KEY(collection_name,source_id)
);
CREATE FUNCTION public.pg_primary_legacy_collection(c text) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
 SELECT c=ANY(ARRAY['enil_news','enli_news_title_translation','enli_news_translation','enil_user','enil_push_tokens',
 'enil_auth_user','enil_auth_session','enil_auth_account','enil_auth_verification','enil_auth_identity'])
$$;
CREATE OR REPLACE FUNCTION public.pg_primary_require_writer() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM public.pg_primary_authority WHERE singleton AND authority='postgresql')
 AND current_setting('levelread.pg_primary',true) IS DISTINCT FROM 'true'
 AND (TG_OP='TRUNCATE' OR NOT public.pg_primary_legacy_collection(TG_TABLE_NAME)
      OR NOT EXISTS(SELECT 1 FROM public.pg_primary_authority WHERE singleton AND legacy_writers_enabled)) THEN
  RAISE EXCEPTION 'PG primary rejects legacy source projection' USING ERRCODE='55000';
 END IF;
 RETURN NULL;
END $$;
CREATE FUNCTION public.pg_primary_changed_keys(a jsonb,b jsonb) RETURNS text[] LANGUAGE sql IMMUTABLE AS $$
 SELECT COALESCE(array_agg(k),'{}'::text[]) FROM (
 SELECT jsonb_object_keys(COALESCE(NULLIF(a,'null'::jsonb),'{}'::jsonb)) AS k
 UNION SELECT jsonb_object_keys(COALESCE(NULLIF(b,'null'::jsonb),'{}'::jsonb))
 ) keys WHERE a->k IS DISTINCT FROM b->k
$$;
CREATE FUNCTION public.pg_primary_keep_keys(incoming jsonb,current_doc jsonb,keys text[]) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE k text; result jsonb:=COALESCE(NULLIF(incoming,'null'::jsonb),'{}'::jsonb);
BEGIN
 FOREACH k IN ARRAY keys LOOP
  IF current_doc ? k THEN result:=jsonb_set(result,ARRAY[k],current_doc->k,true); ELSE result:=result-k; END IF;
 END LOOP;
 RETURN result;
END $$;
CREATE FUNCTION public.pg_primary_projection_document(c text,r jsonb) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE mapping jsonb; pair record; result jsonb;
BEGIN
 mapping:=CASE c
 WHEN 'enil_news' THEN '{"titleid":"titleid","title":"title","summary":"summary","date":"date_ms","originalUrl":"original_url","cover":"cover","public":"is_public","readCount":"read_count","levels":"levels","updatedAt":"updated_at_ms"}'::jsonb
 WHEN 'enil_runtime_config' THEN '{"key":"config_key","enabled":"enabled","authModeDefault":"auth_mode_default","authModeRules":"auth_mode_rules","state":"state","note":"note","internalUserIds":"internal_user_ids","updatedAt":"updated_at_source"}'::jsonb
 WHEN 'enli_news_title_translation' THEN '{"newsId":"news_id","languageCode":"language_code","title":"title","status":"status","provider":"provider","version":"version","createdAt":"created_at_ms","updatedAt":"updated_at_ms"}'::jsonb
 WHEN 'enli_news_translation' THEN '{"newsId":"news_id","languageCode":"language_code","title":"title","summary":"summary","levels":"levels"}'::jsonb
 WHEN 'enil_word_tts' THEN '{"hash_id":"hash_id","filePath":"file_path","createAt":"create_at_ms","pronunciationIpa":"pronunciation_ipa","pronunciationVersion":"pronunciation_version","updatedAt":"updated_at_ms"}'::jsonb
 ELSE NULL END;
 IF mapping IS NULL THEN RETURN COALESCE(NULLIF(r->'source_document','null'::jsonb),'{}'::jsonb); END IF;
 result:=COALESCE(NULLIF(r->'source_extra','null'::jsonb),'{}'::jsonb)||jsonb_build_object('_id',r->'_id');
 FOR pair IN SELECT * FROM jsonb_each_text(mapping) LOOP
  IF r->pair.value IS NOT NULL AND r->pair.value<>'null'::jsonb THEN result:=result||jsonb_build_object(pair.key,r->pair.value); END IF;
 END LOOP;
 RETURN result;
END $$;
CREATE FUNCTION public.pg_primary_track_fields() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE before_row jsonb:='{}'; after_row jsonb:='{}'; cols text[]; docs text[]; extras text[]; id text;
BEGIN
 IF current_setting('levelread.pg_primary',true) IS DISTINCT FROM 'true' THEN RETURN NULL; END IF;
 IF TG_OP<>'INSERT' THEN before_row:=to_jsonb(OLD); END IF;
 IF TG_OP<>'DELETE' THEN after_row:=to_jsonb(NEW); END IF;
 id:=COALESCE(after_row->>'_id',before_row->>'_id');
 cols:=ARRAY(SELECT key FROM unnest(public.pg_primary_changed_keys(before_row,after_row)) AS key WHERE key<>ALL(ARRAY['_id','source_document','source_extra']));
 docs:=public.pg_primary_changed_keys(before_row->'source_document',after_row->'source_document');
 extras:=public.pg_primary_changed_keys(before_row->'source_extra',after_row->'source_extra');
 INSERT INTO public.pg_primary_owned_fields(collection_name,source_id,row_columns,document_fields,extra_fields,created_in_pg,deleted)
 VALUES(TG_TABLE_NAME,id,cols,docs,extras,TG_OP='INSERT',TG_OP='DELETE')
 ON CONFLICT(collection_name,source_id) DO UPDATE SET
 row_columns=ARRAY(SELECT DISTINCT unnest(pg_primary_owned_fields.row_columns||EXCLUDED.row_columns)),
 document_fields=ARRAY(SELECT DISTINCT unnest(pg_primary_owned_fields.document_fields||EXCLUDED.document_fields)),
 extra_fields=ARRAY(SELECT DISTINCT unnest(pg_primary_owned_fields.extra_fields||EXCLUDED.extra_fields)),
 created_in_pg=pg_primary_owned_fields.created_in_pg OR EXCLUDED.created_in_pg,deleted=EXCLUDED.deleted;
 RETURN NULL;
END $$;
CREATE FUNCTION public.pg_primary_merge_legacy() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE ownership public.pg_primary_owned_fields%ROWTYPE; old_row jsonb; next_row jsonb; doc jsonb; id text; expected text; k text; identity_columns text[];
BEGIN
 IF current_setting('levelread.pg_primary',true)='true'
 OR NOT EXISTS(SELECT 1 FROM public.pg_primary_authority WHERE singleton AND authority='postgresql') THEN
  IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
 END IF;
 id:=CASE WHEN TG_OP='DELETE' THEN OLD._id ELSE NEW._id END;
 expected:=format('[%s,%s]',to_json(TG_TABLE_NAME)::text,to_json(id)::text);
 IF current_setting('levelread.guard_key',true) IS DISTINCT FROM expected THEN
  RAISE EXCEPTION 'PG primary requires guarded external writer' USING ERRCODE='55000';
 END IF;
 SELECT * INTO ownership FROM public.pg_primary_owned_fields WHERE collection_name=TG_TABLE_NAME AND source_id=id;
 IF ownership.deleted THEN RAISE EXCEPTION 'PG primary prevents source resurrection' USING ERRCODE='55000'; END IF;
 IF TG_OP='DELETE' THEN
  IF ownership.created_in_pg OR cardinality(ownership.row_columns)>0 THEN
   -- Admin may delete a source article whose only Website edits were counters.
   IF TG_TABLE_NAME<>'enil_news' OR ownership.created_in_pg OR NOT ownership.row_columns<@ARRAY['read_count','updated_at_ms'] OR NOT ownership.document_fields<@ARRAY['readCount','updatedAt'] OR cardinality(ownership.extra_fields)>0
   THEN RAISE EXCEPTION 'PG primary prevents source deletion of owned data' USING ERRCODE='55000'; END IF;
  END IF;
  RETURN OLD;
 END IF;
 next_row:=to_jsonb(NEW);
 IF TG_OP='UPDATE' THEN
  old_row:=to_jsonb(OLD);
  identity_columns:=CASE TG_TABLE_NAME
   WHEN 'enil_user' THEN ARRAY['user_id']
   WHEN 'enil_auth_user' THEN ARRAY['id','canonicalUserId']
   WHEN 'enil_auth_session' THEN ARRAY['id','userId']
   WHEN 'enil_auth_account' THEN ARRAY['id','userId','providerId','accountId']
   WHEN 'enil_auth_identity' THEN ARRAY['provider','provider_user_id','canonical_user_id']
   ELSE ARRAY['_id'] END;
  FOREACH k IN ARRAY identity_columns LOOP
   IF next_row->k IS DISTINCT FROM old_row->k THEN RAISE EXCEPTION 'PG primary external identity mutation' USING ERRCODE='55000'; END IF;
  END LOOP;
  next_row:=public.pg_primary_keep_keys(next_row,old_row,COALESCE(ownership.row_columns,'{}'));
  IF next_row ? 'source_extra' THEN
   next_row:=jsonb_set(next_row,'{source_extra}',public.pg_primary_keep_keys(next_row->'source_extra',old_row->'source_extra',COALESCE(ownership.extra_fields,'{}')));
  END IF;
 END IF;
 doc:=public.pg_primary_projection_document(TG_TABLE_NAME,next_row);
 IF TG_OP='UPDATE' THEN doc:=public.pg_primary_keep_keys(doc,old_row->'source_document',COALESCE(ownership.document_fields,'{}')); END IF;
 next_row:=jsonb_set(next_row,'{source_document}',doc);
 NEW:=jsonb_populate_record(NEW,next_row);
 RETURN NEW;
END $$;
DO $$ DECLARE name text; BEGIN
 FOREACH name IN ARRAY ARRAY['enil_news','enil_runtime_config','enli_news_title_translation','enli_news_translation',
 'enil_word_tts','enil_word_dictionary','enil_user','enil_vocabulary','enil_quiz_answer','enil_level_learning_progress',
 'enil_news_favorite','enil_push_tokens','enil_event_log','enil_auth_user','enil_auth_session',
 'enil_auth_account','enil_auth_verification','enil_auth_identity','enil_subscription_events','enil_user_avatar'] LOOP
  EXECUTE format('CREATE TRIGGER pg_primary_legacy_merge BEFORE INSERT OR UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.pg_primary_merge_legacy()',name);
  EXECUTE format('CREATE TRIGGER pg_primary_ownership_track AFTER INSERT OR UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.pg_primary_track_fields()',name);
 END LOOP;
END $$;
COMMIT;

-- Keep the unchanged Google write-fence store, but do not let a CloudBase
-- pending marker send PG-authoritative OAuth state/new users back to CloudBase.
-- Only the dedicated Google read pool changes admission, only after PG activation.
BEGIN;
ALTER TABLE public.pg_auth_read_pending RENAME TO pg_auth_read_pending_store;
CREATE VIEW public.pg_auth_read_pending AS
 SELECT p.* FROM public.pg_auth_read_pending_store p
 WHERE current_setting('application_name',true) IS DISTINCT FROM 'levelread-google-auth-read'
 OR NOT EXISTS(SELECT 1 FROM public.pg_primary_authority WHERE singleton AND authority='postgresql' AND legacy_writers_enabled);
DO $$ DECLARE permission record; target text; BEGIN
 FOR permission IN SELECT grantee,privilege_type FROM information_schema.role_table_grants
  WHERE table_schema='public' AND table_name='pg_auth_read_pending_store'
  AND privilege_type IN ('SELECT','INSERT','UPDATE','DELETE') LOOP
  target:=CASE WHEN permission.grantee='PUBLIC' THEN 'PUBLIC' ELSE quote_ident(permission.grantee) END;
  EXECUTE format('GRANT %s ON public.pg_auth_read_pending TO %s',permission.privilege_type,target);
 END LOOP;
END $$;
COMMENT ON VIEW public.pg_auth_read_pending IS 'Source-write fence remains visible to writers/recovery. Dedicated Google reads use PG authority after Website-only cutover; no source-read admission fallback for PG-only identities/state.';
COMMIT;

-- PG-only Admin operational state; never touched by source replication.
BEGIN;
CREATE TABLE public.enil_push_jobs (_id text PRIMARY KEY,source_document jsonb NOT NULL);
CREATE TABLE public.enil_push_delivery (_id text PRIMARY KEY,source_document jsonb NOT NULL);
CREATE INDEX enil_push_jobs_job_id_idx ON public.enil_push_jobs ((source_document->>'jobId'));
CREATE INDEX enil_push_delivery_date_idx ON public.enil_push_delivery ((source_document->>'date'));
CREATE TRIGGER pg_primary_writer_fence BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE ON public.enil_push_jobs FOR EACH STATEMENT EXECUTE FUNCTION public.pg_primary_require_writer();
CREATE TRIGGER pg_primary_writer_fence BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE ON public.enil_push_delivery FOR EACH STATEMENT EXECUTE FUNCTION public.pg_primary_require_writer();
COMMIT;

UPDATE public.pg_primary_authority SET authority='postgresql',legacy_writers_enabled=false;