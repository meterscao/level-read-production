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
DROP TABLE public.enil_waitlist;
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
CREATE TABLE public.enil_push_jobs (_id text PRIMARY KEY,source_document jsonb NOT NULL); CREATE TABLE public.enil_push_delivery (_id text PRIMARY KEY,source_document jsonb NOT NULL);-- Fixed business protection; no migration state or configuration tables.
CREATE OR REPLACE FUNCTION public.enforce_business_write() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='TRUNCATE' THEN RAISE EXCEPTION 'Business tables cannot be truncated' USING ERRCODE='55000'; END IF;
 IF current_setting('levelread.business_write',true) IS DISTINCT FROM 'true' THEN
  RAISE EXCEPTION 'Business write requires an application transaction' USING ERRCODE='55000';
 END IF;
 IF TG_OP='UPDATE' AND NEW._id IS DISTINCT FROM OLD._id THEN
  RAISE EXCEPTION 'Physical ID mutation forbidden' USING ERRCODE='55000';
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;
DO $$ DECLARE name text; BEGIN
 FOREACH name IN ARRAY ARRAY['enil_news','enil_runtime_config','enli_news_title_translation','enli_news_translation','enil_word_tts','enil_word_dictionary','enil_user','enil_vocabulary','enil_quiz_answer','enil_level_learning_progress','enil_news_favorite','enil_push_tokens','enil_event_log','enil_auth_user','enil_auth_session','enil_auth_account','enil_auth_verification','enil_auth_identity','enil_subscription_events','enil_user_avatar','enil_push_jobs','enil_push_delivery'] LOOP
  EXECUTE format('DROP TRIGGER IF EXISTS business_write_guard ON public.%I',name);
  EXECUTE format('CREATE TRIGGER business_write_guard BEFORE INSERT OR UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.enforce_business_write()',name);
  EXECUTE format('DROP TRIGGER IF EXISTS business_truncate_guard ON public.%I',name);
  EXECUTE format('CREATE TRIGGER business_truncate_guard BEFORE TRUNCATE ON public.%I FOR EACH STATEMENT EXECUTE FUNCTION public.enforce_business_write()',name);
 END LOOP;
END $$;
