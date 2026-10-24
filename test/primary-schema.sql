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
-- Apply before new application builds. One transaction; rollback on any audit/DDL failure.
BEGIN;
SET LOCAL lock_timeout='15s'; SET LOCAL statement_timeout='180s';
SELECT pg_advisory_xact_lock(hashtextextended('levelread-pg-primary-business',0));
SELECT set_config('levelread.business_write','true',true);
CREATE UNIQUE INDEX enil_user_logical_unique ON public.enil_user (user_id);
CREATE UNIQUE INDEX enil_news_logical_unique ON public.enil_news (titleid);
CREATE UNIQUE INDEX enil_runtime_config_logical_unique ON public.enil_runtime_config (config_key);
CREATE UNIQUE INDEX enil_auth_user_logical_unique ON public.enil_auth_user (id);
CREATE UNIQUE INDEX enil_auth_session_logical_unique ON public.enil_auth_session (token);
CREATE UNIQUE INDEX enil_auth_account_logical_unique ON public.enil_auth_account ("providerId","accountId");
CREATE UNIQUE INDEX enil_auth_verification_logical_unique ON public.enil_auth_verification (id);
CREATE UNIQUE INDEX enil_level_learning_progress_logical_unique ON public.enil_level_learning_progress (user_id,news_id,level);
CREATE UNIQUE INDEX enil_quiz_answer_logical_unique ON public.enil_quiz_answer (user_id,news_id);
CREATE UNIQUE INDEX enil_news_favorite_logical_unique ON public.enil_news_favorite (user_id,news_id);
CREATE UNIQUE INDEX enli_news_translation_logical_unique ON public.enli_news_translation (news_id,language_code);
CREATE UNIQUE INDEX enli_news_title_translation_logical_unique ON public.enli_news_title_translation (news_id,language_code);
CREATE UNIQUE INDEX enil_word_dictionary_logical_unique ON public.enil_word_dictionary (word,language_code);
CREATE UNIQUE INDEX enil_subscription_events_logical_unique ON public.enil_subscription_events (provider,event_id);
CREATE UNIQUE INDEX enil_auth_session_id_unique ON public.enil_auth_session (id);
CREATE UNIQUE INDEX enil_auth_account_id_unique ON public.enil_auth_account (id);
CREATE UNIQUE INDEX enil_auth_user_email_unique ON public.enil_auth_user (lower(email));
CREATE INDEX enil_news_feed_typed ON public.enil_news (is_public,date_ms DESC NULLS LAST,_id);
CREATE INDEX enil_user_role_level ON public.enil_user (role,level,_id);
CREATE TABLE public.enil_user_daily_activity (
 _id text PRIMARY KEY,
 profile_id text NOT NULL REFERENCES public.enil_user(_id) ON DELETE CASCADE,
 position integer NOT NULL CHECK(position>=0), UNIQUE(profile_id,position),
 date text,reading boolean,listening boolean,quiz boolean,
 present_fields text[] NOT NULL,
 extra jsonb NOT NULL CHECK(jsonb_typeof(extra)='object')
);
CREATE TABLE public.enil_user_entitlement (
 _id text PRIMARY KEY,
 profile_id text NOT NULL REFERENCES public.enil_user(_id) ON DELETE CASCADE,
 scope text NOT NULL, is_null boolean NOT NULL, UNIQUE(profile_id,scope),
 price numeric,currency text,price_in_purchased_currency numeric,status text,provider text,product_id text,product_type text,period_type text,environment text,purchased_at_ms bigint,expires_at_ms bigint,store text,original_transaction_id text,transaction_id text,latest_event_id text,latest_event_type text,latest_event_at_ms bigint,
 present_fields text[] NOT NULL,
 extra jsonb NOT NULL CHECK(jsonb_typeof(extra)='object')
);
CREATE INDEX enil_user_daily_activity_date ON public.enil_user_daily_activity(date,profile_id);
CREATE INDEX enil_user_entitlement_status_expiry ON public.enil_user_entitlement(scope,status,expires_at_ms,profile_id);
CREATE FUNCTION public.enil_user_daily_activity_document(r public.enil_user_daily_activity) RETURNS jsonb LANGUAGE sql IMMUTABLE STRICT AS $$
 SELECT r.extra || COALESCE((SELECT jsonb_object_agg(k,v) FROM jsonb_each(jsonb_build_object('date',r.date,'reading',r.reading,'listening',r.listening,'quiz',r.quiz)) e(k,v) WHERE k=ANY(r.present_fields)),'{}'::jsonb)
$$;
CREATE FUNCTION public.enil_user_entitlement_document(r public.enil_user_entitlement) RETURNS jsonb LANGUAGE sql IMMUTABLE STRICT AS $$
 SELECT CASE WHEN r.is_null THEN 'null'::jsonb ELSE r.extra || COALESCE((SELECT jsonb_object_agg(k,v) FROM jsonb_each(jsonb_build_object('price',r.price,'currency',r.currency,'priceInPurchasedCurrency',r.price_in_purchased_currency,'status',r.status,'provider',r.provider,'productId',r.product_id,'productType',r.product_type,'periodType',r.period_type,'environment',r.environment,'purchasedAt',r.purchased_at_ms,'expiresAt',r.expires_at_ms,'store',r.store,'originalTransactionId',r.original_transaction_id,'transactionId',r.transaction_id,'latestEventId',r.latest_event_id,'latestEventType',r.latest_event_type,'latestEventAt',r.latest_event_at_ms)) e(k,v) WHERE k=ANY(r.present_fields)),'{}'::jsonb) END
$$;
CREATE FUNCTION public.user_profile_document(u public.enil_user) RETURNS jsonb LANGUAGE sql STABLE STRICT AS $$
 SELECT u.source_document ||
 CASE WHEN jsonb_typeof(u.source_document->'streakDayList')='array' THEN jsonb_build_object('streakDayList',COALESCE((SELECT jsonb_agg(public.enil_user_daily_activity_document(a) ORDER BY a.position) FROM public.enil_user_daily_activity a WHERE a.profile_id=u._id),'[]'::jsonb)) ELSE '{}'::jsonb END ||
 CASE WHEN jsonb_typeof(u.source_document->'subscription')='object' THEN jsonb_build_object('subscription',COALESCE((SELECT public.enil_user_entitlement_document(e) FROM public.enil_user_entitlement e WHERE e.profile_id=u._id AND e.scope='LEGACY'),'{}'::jsonb)) ELSE '{}'::jsonb END ||
 CASE WHEN jsonb_typeof(u.source_document->'subscriptionByEnv')='object' THEN jsonb_build_object('subscriptionByEnv',COALESCE((SELECT jsonb_object_agg(e.scope,public.enil_user_entitlement_document(e)) FROM public.enil_user_entitlement e WHERE e.profile_id=u._id AND e.scope<>'LEGACY'),'{}'::jsonb)) ELSE '{}'::jsonb END
$$;
-- During expansion this retains the complete payload for old readers. Contract replaces its body.
CREATE FUNCTION public.user_profile_payload(d jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE STRICT AS $$ SELECT d $$;
CREATE FUNCTION public.write_user_relations(profile text,d jsonb) RETURNS void LANGUAGE plpgsql AS $$
DECLARE item jsonb; slot text; n integer; shape text;
BEGIN
 IF current_setting('levelread.business_write',true) IS DISTINCT FROM 'true' THEN RAISE EXCEPTION 'Business write requires an application transaction' USING ERRCODE='55000'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.enil_user WHERE _id=profile) THEN RAISE EXCEPTION 'Missing user profile' USING ERRCODE='23503'; END IF;
 shape=jsonb_typeof(d->'streakDayList');
 IF shape IS NOT NULL AND shape NOT IN ('array','null') THEN RAISE EXCEPTION 'Invalid daily activity container' USING ERRCODE='22023'; END IF;
 n=0;
 FOR item IN SELECT v FROM jsonb_array_elements(CASE WHEN shape='array' THEN d->'streakDayList' ELSE '[]' END) x(v) LOOP
  IF jsonb_typeof(item)<>'object' THEN RAISE EXCEPTION 'Invalid daily activity' USING ERRCODE='22023'; END IF;

  IF item ? 'date' AND jsonb_typeof(item->'date') NOT IN ('string','null') THEN RAISE EXCEPTION 'Invalid daily activity date' USING ERRCODE='22023'; END IF;
  IF item ? 'reading' AND jsonb_typeof(item->'reading') NOT IN ('boolean','null') THEN RAISE EXCEPTION 'Invalid daily activity reading' USING ERRCODE='22023'; END IF;
  IF item ? 'listening' AND jsonb_typeof(item->'listening') NOT IN ('boolean','null') THEN RAISE EXCEPTION 'Invalid daily activity listening' USING ERRCODE='22023'; END IF;
  IF item ? 'quiz' AND jsonb_typeof(item->'quiz') NOT IN ('boolean','null') THEN RAISE EXCEPTION 'Invalid daily activity quiz' USING ERRCODE='22023'; END IF;
  INSERT INTO public.enil_user_daily_activity AS current (_id,profile_id,position,date,reading,listening,quiz,present_fields,extra) VALUES (length(profile)::text||':'||profile||':'||n::text,profile,n,(item->>'date')::text,(item->>'reading')::boolean,(item->>'listening')::boolean,(item->>'quiz')::boolean,ARRAY(SELECT jsonb_object_keys(CASE WHEN jsonb_typeof(item)='object' THEN item ELSE '{}' END)),CASE WHEN jsonb_typeof(item)='object' THEN item ELSE '{}'::jsonb END - ARRAY['date','reading','listening','quiz'])
  ON CONFLICT(_id) DO UPDATE SET position=EXCLUDED.position,date=EXCLUDED.date,reading=EXCLUDED.reading,listening=EXCLUDED.listening,quiz=EXCLUDED.quiz,present_fields=EXCLUDED.present_fields,extra=EXCLUDED.extra
  WHERE ROW(current.position,current.date,current.reading,current.listening,current.quiz,current.present_fields,current.extra) IS DISTINCT FROM ROW(EXCLUDED.position,EXCLUDED.date,EXCLUDED.reading,EXCLUDED.listening,EXCLUDED.quiz,EXCLUDED.present_fields,EXCLUDED.extra);
  n=n+1;
 END LOOP;
 DELETE FROM public.enil_user_daily_activity WHERE profile_id=profile AND position>=n;
 shape=jsonb_typeof(d->'subscription');
 IF shape IS NOT NULL AND shape NOT IN ('object','null') THEN RAISE EXCEPTION 'Invalid legacy entitlement' USING ERRCODE='22023'; END IF;
 shape=jsonb_typeof(d->'subscriptionByEnv');
 IF shape IS NOT NULL AND shape NOT IN ('object','null') THEN RAISE EXCEPTION 'Invalid entitlement container' USING ERRCODE='22023'; END IF;
 IF (d->'subscriptionByEnv') ? 'LEGACY' THEN RAISE EXCEPTION 'Reserved entitlement scope' USING ERRCODE='22023'; END IF;
 FOR slot,item IN
  SELECT 'LEGACY',d->'subscription' WHERE jsonb_typeof(d->'subscription')='object'
  UNION ALL SELECT k,v FROM jsonb_each(CASE WHEN shape='object' THEN d->'subscriptionByEnv' ELSE '{}' END) e(k,v)
 LOOP
  IF jsonb_typeof(item) NOT IN ('object','null') THEN RAISE EXCEPTION 'Invalid entitlement' USING ERRCODE='22023'; END IF;

  IF item ? 'price' AND jsonb_typeof(item->'price') NOT IN ('number','null') THEN RAISE EXCEPTION 'Invalid entitlement price' USING ERRCODE='22023'; END IF;
  IF item ? 'currency' AND jsonb_typeof(item->'currency') NOT IN ('string','null') THEN RAISE EXCEPTION 'Invalid entitlement currency' USING ERRCODE='22023'; END IF;
  IF item ? 'priceInPurchasedCurrency' AND jsonb_typeof(item->'priceInPurchasedCurrency') NOT IN ('number','null') THEN RAISE EXCEPTION 'Invalid entitlement priceInPurchasedCurrency' USING ERRCODE='22023'; END IF;
  IF item ? 'status' AND jsonb_typeof(item->'status') NOT IN ('string','null') THEN RAISE EXCEPTION 'Invalid entitlement status' USING ERRCODE='22023'; END IF;
  IF item ? 'provider' AND jsonb_typeof(item->'provider') NOT IN ('string','null') THEN RAISE EXCEPTION 'Invalid entitlement provider' USING ERRCODE='22023'; END IF;
  IF item ? 'productId' AND jsonb_typeof(item->'productId') NOT IN ('string','null') THEN RAISE EXCEPTION 'Invalid entitlement productId' USING ERRCODE='22023'; END IF;
  IF item ? 'productType' AND jsonb_typeof(item->'productType') NOT IN ('string','null') THEN RAISE EXCEPTION 'Invalid entitlement productType' USING ERRCODE='22023'; END IF;
  IF item ? 'periodType' AND jsonb_typeof(item->'periodType') NOT IN ('string','null') THEN RAISE EXCEPTION 'Invalid entitlement periodType' USING ERRCODE='22023'; END IF;
  IF item ? 'environment' AND jsonb_typeof(item->'environment') NOT IN ('string','null') THEN RAISE EXCEPTION 'Invalid entitlement environment' USING ERRCODE='22023'; END IF;
  IF item ? 'purchasedAt' AND jsonb_typeof(item->'purchasedAt') NOT IN ('number','null') THEN RAISE EXCEPTION 'Invalid entitlement purchasedAt' USING ERRCODE='22023'; END IF;
  IF item ? 'expiresAt' AND jsonb_typeof(item->'expiresAt') NOT IN ('number','null') THEN RAISE EXCEPTION 'Invalid entitlement expiresAt' USING ERRCODE='22023'; END IF;
  IF item ? 'store' AND jsonb_typeof(item->'store') NOT IN ('string','null') THEN RAISE EXCEPTION 'Invalid entitlement store' USING ERRCODE='22023'; END IF;
  IF item ? 'originalTransactionId' AND jsonb_typeof(item->'originalTransactionId') NOT IN ('string','null') THEN RAISE EXCEPTION 'Invalid entitlement originalTransactionId' USING ERRCODE='22023'; END IF;
  IF item ? 'transactionId' AND jsonb_typeof(item->'transactionId') NOT IN ('string','null') THEN RAISE EXCEPTION 'Invalid entitlement transactionId' USING ERRCODE='22023'; END IF;
  IF item ? 'latestEventId' AND jsonb_typeof(item->'latestEventId') NOT IN ('string','null') THEN RAISE EXCEPTION 'Invalid entitlement latestEventId' USING ERRCODE='22023'; END IF;
  IF item ? 'latestEventType' AND jsonb_typeof(item->'latestEventType') NOT IN ('string','null') THEN RAISE EXCEPTION 'Invalid entitlement latestEventType' USING ERRCODE='22023'; END IF;
  IF item ? 'latestEventAt' AND jsonb_typeof(item->'latestEventAt') NOT IN ('number','null') THEN RAISE EXCEPTION 'Invalid entitlement latestEventAt' USING ERRCODE='22023'; END IF;
  INSERT INTO public.enil_user_entitlement AS current (_id,profile_id,scope,is_null,price,currency,price_in_purchased_currency,status,provider,product_id,product_type,period_type,environment,purchased_at_ms,expires_at_ms,store,original_transaction_id,transaction_id,latest_event_id,latest_event_type,latest_event_at_ms,present_fields,extra) VALUES (length(profile)::text||':'||profile||':'||slot,profile,slot,jsonb_typeof(item)='null',(item->>'price')::numeric,(item->>'currency')::text,(item->>'priceInPurchasedCurrency')::numeric,(item->>'status')::text,(item->>'provider')::text,(item->>'productId')::text,(item->>'productType')::text,(item->>'periodType')::text,(item->>'environment')::text,(item->>'purchasedAt')::bigint,(item->>'expiresAt')::bigint,(item->>'store')::text,(item->>'originalTransactionId')::text,(item->>'transactionId')::text,(item->>'latestEventId')::text,(item->>'latestEventType')::text,(item->>'latestEventAt')::bigint,ARRAY(SELECT jsonb_object_keys(CASE WHEN jsonb_typeof(item)='object' THEN item ELSE '{}' END)),CASE WHEN jsonb_typeof(item)='object' THEN item ELSE '{}'::jsonb END - ARRAY['price','currency','priceInPurchasedCurrency','status','provider','productId','productType','periodType','environment','purchasedAt','expiresAt','store','originalTransactionId','transactionId','latestEventId','latestEventType','latestEventAt'])
  ON CONFLICT(_id) DO UPDATE SET scope=EXCLUDED.scope,is_null=EXCLUDED.is_null,price=EXCLUDED.price,currency=EXCLUDED.currency,price_in_purchased_currency=EXCLUDED.price_in_purchased_currency,status=EXCLUDED.status,provider=EXCLUDED.provider,product_id=EXCLUDED.product_id,product_type=EXCLUDED.product_type,period_type=EXCLUDED.period_type,environment=EXCLUDED.environment,purchased_at_ms=EXCLUDED.purchased_at_ms,expires_at_ms=EXCLUDED.expires_at_ms,store=EXCLUDED.store,original_transaction_id=EXCLUDED.original_transaction_id,transaction_id=EXCLUDED.transaction_id,latest_event_id=EXCLUDED.latest_event_id,latest_event_type=EXCLUDED.latest_event_type,latest_event_at_ms=EXCLUDED.latest_event_at_ms,present_fields=EXCLUDED.present_fields,extra=EXCLUDED.extra
  WHERE ROW(current.scope,current.is_null,current.price,current.currency,current.price_in_purchased_currency,current.status,current.provider,current.product_id,current.product_type,current.period_type,current.environment,current.purchased_at_ms,current.expires_at_ms,current.store,current.original_transaction_id,current.transaction_id,current.latest_event_id,current.latest_event_type,current.latest_event_at_ms,current.present_fields,current.extra) IS DISTINCT FROM ROW(EXCLUDED.scope,EXCLUDED.is_null,EXCLUDED.price,EXCLUDED.currency,EXCLUDED.price_in_purchased_currency,EXCLUDED.status,EXCLUDED.provider,EXCLUDED.product_id,EXCLUDED.product_type,EXCLUDED.period_type,EXCLUDED.environment,EXCLUDED.purchased_at_ms,EXCLUDED.expires_at_ms,EXCLUDED.store,EXCLUDED.original_transaction_id,EXCLUDED.transaction_id,EXCLUDED.latest_event_id,EXCLUDED.latest_event_type,EXCLUDED.latest_event_at_ms,EXCLUDED.present_fields,EXCLUDED.extra);
 END LOOP;
 DELETE FROM public.enil_user_entitlement e WHERE e.profile_id=profile AND NOT (
  (e.scope='LEGACY' AND jsonb_typeof(d->'subscription')='object') OR
  (e.scope<>'LEGACY' AND COALESCE(d->'subscriptionByEnv','{}') ? e.scope)
 ) IS TRUE;
END $$;
CREATE FUNCTION public.bridge_user_relations() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM public.write_user_relations(NEW._id,NEW.source_document);
 RETURN NEW;
END $$;
CREATE TRIGGER user_relations_compat AFTER INSERT OR UPDATE ON public.enil_user FOR EACH ROW EXECUTE FUNCTION public.bridge_user_relations();
DO $$ DECLARE name text; BEGIN
 FOREACH name IN ARRAY ARRAY['enil_user_daily_activity','enil_user_entitlement'] LOOP
  EXECUTE format('CREATE TRIGGER business_write_guard BEFORE INSERT OR UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.enforce_business_write()',name);
  EXECUTE format('CREATE TRIGGER business_truncate_guard BEFORE TRUNCATE ON public.%I FOR EACH STATEMENT EXECUTE FUNCTION public.enforce_business_write()',name);
 END LOOP;
END $$;
COMMIT;
-- Only after all four entrypoints use the new shared runtime. No feature/state table.
BEGIN;
SET LOCAL lock_timeout='15s'; SET LOCAL statement_timeout='180s';
SELECT pg_advisory_xact_lock(hashtextextended('levelread-pg-primary-business',0));
SELECT set_config('levelread.business_write','true',true);
DROP TRIGGER IF EXISTS user_relations_compat ON public.enil_user;
DROP FUNCTION IF EXISTS public.bridge_user_relations();
CREATE OR REPLACE FUNCTION public.user_profile_payload(d jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE STRICT AS $$
 SELECT d || CASE WHEN jsonb_typeof(d->'streakDayList')='array' THEN '{"streakDayList":[]}'::jsonb ELSE '{}'::jsonb END
 || CASE WHEN jsonb_typeof(d->'subscription')='object' THEN '{"subscription":{}}'::jsonb ELSE '{}'::jsonb END
 || CASE WHEN jsonb_typeof(d->'subscriptionByEnv')='object' THEN '{"subscriptionByEnv":{}}'::jsonb ELSE '{}'::jsonb END
$$;
COMMIT;
-- Run only after every profile payload is compact; the operator runner checks this.
BEGIN;
SET LOCAL lock_timeout='15s'; SET LOCAL statement_timeout='30s';
SELECT pg_advisory_xact_lock(hashtextextended('levelread-pg-primary-business',0));
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM public.enil_user WHERE source_document IS DISTINCT FROM public.user_profile_payload(source_document)) THEN
  RAISE EXCEPTION 'Full user relation payloads remain';
 END IF;
END $$;
ALTER TABLE public.enil_user DROP COLUMN IF EXISTS streak_day_list, DROP COLUMN IF EXISTS subscription, DROP COLUMN IF EXISTS subscription_by_env;
COMMIT;
