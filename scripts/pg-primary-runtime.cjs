"use strict";
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// scripts/pg-primary-ingest.ts
var pg_primary_ingest_exports = {};
__export(pg_primary_ingest_exports, {
  createPrimaryDatabase: () => createPrimaryDatabase,
  ingest: () => ingest,
  run: () => run
});
module.exports = __toCommonJS(pg_primary_ingest_exports);
var import_node_crypto4 = require("node:crypto");
var import_pg2 = require("pg");

// lib/db/pg-primary.ts
var import_node_async_hooks = require("node:async_hooks");
var import_node_crypto3 = require("node:crypto");
var import_pg = require("pg");

// lib/postgres/config.ts
var import_node_fs = require("node:fs");
var import_node_tls = require("node:tls");

// lib/postgres/types.ts
var PgPersistenceError = class extends Error {
  constructor(code) {
    super(code);
    this.code = code;
    this.name = "PgPersistenceError";
  }
  code;
};

// lib/postgres/config.ts
function poolOptions(env = process.env) {
  try {
    const url = new URL(env.DATABASE_URL || "");
    if (!["postgres:", "postgresql:"].includes(url.protocol) || !url.hostname || !url.username || !url.password || decodeURIComponent(url.pathname.slice(1)) !== "levelread_prod" || !env.PG_SSL_CA_FILE)
      throw new Error();
    if (Array.from(url.searchParams.keys()).some(
      (key) => !["sslmode"].includes(key)
    ) || url.searchParams.has("sslmode") && url.searchParams.get("sslmode") !== "verify-full")
      throw new Error();
    const ca = (0, import_node_fs.readFileSync)(env.PG_SSL_CA_FILE, "utf8");
    if (!ca.includes("-----BEGIN CERTIFICATE-----")) throw new Error();
    return {
      host: url.hostname,
      port: Number(url.port || 5432),
      database: "levelread_prod",
      user: decodeURIComponent(url.username),
      password: decodeURIComponent(url.password),
      ssl: {
        ca,
        rejectUnauthorized: true,
        checkServerIdentity: (_hostname, cert) => (0, import_node_tls.checkServerIdentity)(url.hostname, cert)
      },
      max: 2,
      connectionTimeoutMillis: 1e3,
      idleTimeoutMillis: 1e4,
      application_name: "levelread-website"
    };
  } catch {
    throw new PgPersistenceError("configuration");
  }
}

// lib/postgres/collections.ts
var ORDINARY_COLLECTIONS = [
  "enil_news",
  "enli_news_title_translation",
  "enli_news_translation",
  "enil_word_dictionary",
  "enil_word_tts",
  "enil_user",
  "enil_vocabulary",
  "enil_quiz_answer",
  "enil_level_learning_progress",
  "enil_news_favorite",
  "enil_push_tokens",
  "enil_event_log"
];
var OWNED_COLLECTIONS = [
  "enil_user",
  "enil_vocabulary",
  "enil_quiz_answer",
  "enil_level_learning_progress",
  "enil_news_favorite"
];
var AUTH_COLLECTIONS = [
  "enil_auth_user",
  "enil_auth_session",
  "enil_auth_account",
  "enil_auth_verification",
  "enil_auth_identity"
];
var CONFIG_COLLECTIONS = ["enil_runtime_config"];
var DOCUMENT_COLLECTIONS = [
  ...ORDINARY_COLLECTIONS,
  ...CONFIG_COLLECTIONS,
  ...AUTH_COLLECTIONS,
  "enil_push_jobs",
  "enil_push_delivery"
];

// lib/postgres/mapping.ts
function sourceJson(value2, ancestors = /* @__PURE__ */ new Set()) {
  if (value2 === null || typeof value2 === "boolean") return value2;
  if (typeof value2 === "string") {
    if (value2.includes("\0")) throw new PgPersistenceError("mapping");
    return value2;
  }
  if (typeof value2 === "number") {
    if (!Number.isFinite(value2)) throw new PgPersistenceError("mapping");
    return value2;
  }
  if (value2 instanceof Date) {
    if (!Number.isFinite(value2.getTime()))
      throw new PgPersistenceError("mapping");
    return { __cloudbaseDate: value2.toISOString() };
  }
  if (!value2 || typeof value2 !== "object" || ancestors.has(value2))
    throw new PgPersistenceError("mapping");
  ancestors.add(value2);
  try {
    if (Array.isArray(value2))
      return value2.map(
        (v) => v === void 0 ? null : sourceJson(v, ancestors)
      );
    if (Object.getPrototypeOf(value2) !== Object.prototype && Object.getPrototypeOf(value2) !== null)
      throw new PgPersistenceError("mapping");
    return Object.fromEntries(
      Object.entries(value2).filter(([, v]) => v !== void 0).map(([k, v]) => {
        if (k.includes("\0")) throw new PgPersistenceError("mapping");
        return [k, sourceJson(v, ancestors)];
      })
    );
  } finally {
    ancestors.delete(value2);
  }
}

// lib/postgres/projections.ts
var import_node_crypto = require("node:crypto");
var snake = (value2) => value2.replace(/[A-Z]/g, (char) => "_" + char.toLowerCase());
function fields(kind, names) {
  return names.split(" ").filter(Boolean).map((pair) => {
    const [source, column] = pair.split(":");
    return {
      source,
      column: column || snake(source) + (kind === "integer" && /At$|Timestamp$/.test(source) ? "_ms" : ""),
      kind
    };
  });
}
var text = (s) => fields("text", s);
var integer = (s) => fields("integer", s);
var array = (s) => fields("array", s);
var date = (s) => fields("date", s);
var boolean = (s) => fields("boolean", s);
function authFields(fields2) {
  return fields2.map((field) => ({ ...field, column: field.source }));
}
var definitions = {
  enil_push_jobs: [
    ...text("jobId taskType status sendMode todayDate audience newsId"),
    ...integer("maxUsers skipUsers"),
    ...date("createdAt updatedAt startedAt finishedAt completedAt")
  ],
  enil_push_delivery: [
    ...text("kind date owner tokenId state leaseToken ticketId code"),
    ...integer("attempts leaseUntil nextAttemptAt updatedAt")
  ],
  enil_runtime_config: [
    ...text("key:config_key authModeDefault state note"),
    ...boolean("enabled"),
    ...array("authModeRules internalUserIds"),
    ...fields("epochDate", "updatedAt:updated_at"),
    ...fields("raw", "updatedAt:updated_at_source")
  ],
  enil_auth_user: authFields([
    ...text("id name email image canonicalUserId"),
    ...boolean("emailVerified"),
    ...date("createdAt updatedAt")
  ]),
  enil_auth_session: authFields([
    ...text("id token ipAddress userAgent userId authSource"),
    ...date("expiresAt createdAt updatedAt")
  ]),
  enil_auth_account: authFields([
    ...text(
      "id accountId providerId userId accessToken refreshToken idToken scope password"
    ),
    ...date("accessTokenExpiresAt refreshTokenExpiresAt createdAt updatedAt")
  ]),
  enil_auth_verification: authFields([
    ...text("id identifier value"),
    ...date("expiresAt createdAt updatedAt")
  ]),
  enil_auth_identity: [
    ...text("provider providerUserId canonicalUserId email"),
    ...date("createdAt updatedAt")
  ],
  enil_news: [
    ...text("titleid title summary originalUrl:original_url cover"),
    ...integer("date:date_ms readCount:read_count updatedAt"),
    ...boolean("public:is_public"),
    ...array("levels")
  ],
  enli_news_title_translation: [
    ...text("newsId languageCode title status provider version"),
    ...integer("createdAt updatedAt")
  ],
  enli_news_translation: [
    ...text("newsId languageCode title summary"),
    ...array("levels")
  ],
  enil_word_dictionary: [
    ...text("word languageCode phoneticUS:phonetic_us phoneticUK:phonetic_uk"),
    ...array("parts"),
    ...integer("updatedAt")
  ],
  enil_word_tts: [
    ...text("hash_id filePath pronunciationIpa pronunciationVersion"),
    ...integer("createAt:create_at_ms updatedAt")
  ],
  enil_user: [
    ...text("userId languageCode appLanguageMode"),
    ...integer(
      "level newsRead wordsRead appLanguageOnboardingVersion updatedAt"
    ),
    ...fields("number", "minutesRead"),
    ...boolean(
      "favoriteWordsHighlightEnabled subscriptionEmailNotificationsEnabled"
    ),
    ...array("streakDayList")
  ],
  enil_vocabulary: [
    ...text("userId newsId word explanation"),
    ...fields("levelNumber", "level:level_number"),
    ...date("createdAt lastReviewAt"),
    ...boolean("mastered isKnown"),
    ...integer("reviewCount correctCount wrongCount updatedAt")
  ],
  enil_quiz_answer: [
    ...text("userId newsId"),
    ...array("quizAnswer"),
    ...integer("updatedAt")
  ],
  enil_level_learning_progress: [
    ...text("userId newsId"),
    ...integer(
      "level readingCompletedAt listeningCompletedAt quizCompletedAt completedAt createdAt updatedAt"
    )
  ],
  enil_news_favorite: [
    ...text("userId newsId titleid"),
    ...integer("level updatedAt"),
    ...date("createdAt")
  ],
  enil_push_tokens: [
    ...text("userId token"),
    ...date("createdAt"),
    ...integer("updatedAt")
  ],
  enil_event_log: [
    ...text(
      "timestamp level service environment method path type source action outcome"
    ),
    ...date("createdAt"),
    ...fields("object", "actor target metadata request")
  ]
};
function ownerColumn(collection) {
  return OWNED_COLLECTIONS.includes(collection) ? "user_id" : void 0;
}
function value(field, doc) {
  const v = doc[field.source];
  if (field.kind === "raw") return JSON.stringify(sourceJson(v ?? null));
  if (field.kind === "epochDate") {
    if (v instanceof Date && Number.isFinite(v.getTime()))
      return v.toISOString();
    if (Number.isSafeInteger(v) && Number.isFinite(new Date(v).getTime()))
      return new Date(v).toISOString();
    throw new PgPersistenceError("mapping");
  }
  if (v === void 0) return null;
  if (v === null)
    return ["array", "object", "level"].includes(field.kind) ? "null" : null;
  if (field.kind === "levelNumber") return typeof v === "number" ? v : null;
  if (field.kind === "text" && typeof v === "string") return v;
  if (field.kind === "integer" && Number.isSafeInteger(v)) return v;
  if (field.kind === "number" && typeof v === "number" && Number.isFinite(v))
    return v;
  if (field.kind === "boolean" && typeof v === "boolean") return v;
  if (field.kind === "date" && v instanceof Date && Number.isFinite(v.getTime()))
    return v.toISOString();
  if (field.kind === "array" && Array.isArray(v))
    return JSON.stringify(sourceJson(v));
  if (field.kind === "object" && typeof v === "object" && !Array.isArray(v) && !(v instanceof Date))
    return JSON.stringify(sourceJson(v));
  if (field.kind === "level" && (typeof v === "string" || Number.isSafeInteger(v)))
    return JSON.stringify(v);
  throw new PgPersistenceError("mapping");
}
function projectDocument(ref, source, previous) {
  if (source._id !== ref.sourceId || ownerColumn(ref.collection) && source.userId !== ref.ownerId)
    throw new PgPersistenceError("ownership");
  const projectedFields = storageFields(ref.collection).filter(
    (field) => !(ref.collection === "enil_user" && field.source === "data" && !Object.hasOwn(source, "data") && !Object.hasOwn(previous ?? {}, "data"))
  );
  const raw = sourceJson(source);
  const columns = [
    "_id",
    ...projectedFields.map((field) => field.column),
    "source_document"
  ];
  const json = JSON.stringify(raw);
  const values = [
    ref.sourceId,
    ...projectedFields.map((field) => value(field, source)),
    json
  ];
  const assignments = columns.slice(1).map((column) => `"${column}"=EXCLUDED."${column}"`);
  assignments.push("document_fields=EXCLUDED.document_fields");
  const owner = ownerColumn(ref.collection);
  return {
    digest: (0, import_node_crypto.createHash)("sha256").update(json).digest("hex"),
    values,
    columns,
    userRawKeys: Object.keys(source),
    jsonColumns: [
      ...projectedFields.filter(
        (field) => ["array", "object", "level", "raw"].includes(field.kind)
      ).map((field) => field.column),
      "source_document"
    ],
    sql: `INSERT INTO public.${ref.collection} (${columns.map((column) => '"' + column + '"').join(",")}) VALUES (${values.map((_, i) => ref.collection === "enil_user" && columns[i] === "source_document" ? `public.user_profile_payload($${i + 1}::jsonb)` : "$" + (i + 1)).join(",")})
      ON CONFLICT (_id) DO UPDATE SET ${assignments.join(",")}
      ${owner ? `WHERE ${ref.collection}.${owner}=EXCLUDED.${owner}` : ""} RETURNING _id`
  };
}
function storageFields(collection) {
  if (collection === "enil_user_avatar")
    return [...text("userId"), ...integer("revision")];
  if (collection === "enil_subscription_events")
    return [
      ...text(
        "userId provider eventId eventType transactionId originalTransactionId productId store environment currency rawPayloadJson:raw_payload_text"
      ),
      ...integer("eventTimestamp purchasedAt expiresAt createdAt updatedAt"),
      ...fields("number", "price"),
      ...fields("raw", "rawPayload:raw_payload")
    ];
  const mapped = definitions[collection];
  if (!mapped) throw Error("pg_storage_collection");
  const mappedFields = collection === "enil_user" ? [
    ...mapped.filter((field) => field.source !== "streakDayList"),
    ...text("role"),
    ...fields("object", "clerkData"),
    ...fields("raw", "data")
  ] : mapped;
  return Array.from(
    new Map(mappedFields.map((field) => [field.source, field])).values()
  );
}
var storageCollections = [
  ...Object.keys(definitions),
  "enil_user_avatar",
  "enil_subscription_events"
];

// lib/postgres/event-projection.ts
var import_node_crypto2 = require("node:crypto");
function eventProjection(sourceId, ownerId, doc) {
  if (doc._id !== sourceId || doc.userId !== ownerId)
    throw new PgPersistenceError("ownership");
  const text2 = [
    "userId",
    "provider",
    "eventId",
    "eventType",
    "transactionId",
    "originalTransactionId",
    "productId",
    "store",
    "environment",
    "currency"
  ];
  const integer2 = [
    "eventTimestamp",
    "purchasedAt",
    "expiresAt",
    "createdAt",
    "updatedAt"
  ];
  const snake2 = (key) => key.replace(/[A-Z]/g, (char) => "_" + char.toLowerCase());
  const columns = [
    "_id",
    ...text2.map(snake2),
    ...integer2.map((key) => snake2(key) + "_ms"),
    "price",
    "raw_payload",
    "raw_payload_text",
    "source_document"
  ];
  const values = [sourceId];
  for (const key of text2) {
    if (doc[key] != null && typeof doc[key] !== "string")
      throw new PgPersistenceError("mapping");
    values.push(doc[key] ?? null);
  }
  for (const key of integer2) {
    if (doc[key] != null && !Number.isSafeInteger(doc[key]))
      throw new PgPersistenceError("mapping");
    values.push(doc[key] ?? null);
  }
  if (doc.price != null && (typeof doc.price !== "number" || !Number.isFinite(doc.price)))
    throw new PgPersistenceError("mapping");
  const rawPayload = doc.rawPayload;
  if (doc.rawPayloadJson !== void 0) {
    if (typeof doc.rawPayloadJson !== "string")
      throw new PgPersistenceError("mapping");
    try {
      JSON.parse(doc.rawPayloadJson);
    } catch {
      throw new PgPersistenceError("mapping");
    }
  }
  if (rawPayload != null && (typeof rawPayload !== "object" || Array.isArray(rawPayload)))
    throw new PgPersistenceError("mapping");
  const json = JSON.stringify(sourceJson(doc));
  values.push(
    doc.price ?? null,
    rawPayload === void 0 ? null : JSON.stringify(sourceJson(rawPayload)),
    doc.rawPayloadJson ?? null,
    json
  );
  return {
    values,
    columns,
    jsonColumns: ["raw_payload", "source_document"],
    userRawKeys: [],
    digest: (0, import_node_crypto2.createHash)("sha256").update(json).digest("hex"),
    sql: `INSERT INTO public.enil_subscription_events (${columns.join(",")}) VALUES (${values.map((_, i) => "$" + (i + 1)).join(",")})
      ON CONFLICT (_id) DO UPDATE SET ${columns.slice(1).map((key) => `${key}=EXCLUDED.${key}`).join(",")},document_fields=EXCLUDED.document_fields
      WHERE enil_subscription_events.user_id=EXCLUDED.user_id RETURNING _id`
  };
}

// lib/postgres/lean-document.ts
function leanDocument(collection, fields2, param, fullDocument) {
  const mapped = new Map(
    storageFields(collection).map((field) => [field.source, field])
  );
  const pairs = Array.from(new Set(fields2)).map((key) => {
    const name = param(key), raw = `(t.source_document::jsonb)->${name}`;
    let value2;
    if (key === "_id")
      value2 = `CASE WHEN (t.source_document::jsonb) ? ${name} THEN ${raw} ELSE to_jsonb(t._id) END`;
    else if (collection === "enil_user" && ["streakDayList", "subscription", "subscriptionByEnv"].includes(key)) {
      let relation;
      if (key === "streakDayList")
        relation = `COALESCE((SELECT jsonb_agg(public.enil_user_daily_activity_document(a) ORDER BY a.position) FROM public.enil_user_daily_activity a WHERE a.profile_id=t._id),'[]'::jsonb)`;
      else if (key === "subscription")
        relation = `COALESCE((SELECT public.enil_user_entitlement_document(e) FROM public.enil_user_entitlement e WHERE e.profile_id=t._id AND e.scope='LEGACY'),'{}'::jsonb)`;
      else
        relation = `COALESCE((SELECT jsonb_object_agg(e.scope,public.enil_user_entitlement_document(e)) FROM public.enil_user_entitlement e WHERE e.profile_id=t._id AND e.scope<>'LEGACY'),'{}'::jsonb)`;
      value2 = `CASE WHEN jsonb_typeof(${raw})='${key === "streakDayList" ? "array" : "object"}' THEN ${relation} ELSE ${raw} END`;
    } else {
      const field = mapped.get(key);
      if (!field) value2 = raw;
      else {
        const column = `t."${field.column}"`;
        const encoded = field.kind === "date" ? `CASE WHEN ${column} IS NULL THEN 'null'::jsonb ELSE jsonb_build_object('__cloudbaseDate',to_char(${column} AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')) END` : `COALESCE(to_jsonb(${column}),'null'::jsonb)`;
        value2 = `CASE WHEN (t.source_document::jsonb) ? ${name} THEN ${raw} WHEN ${name}=ANY(t.document_fields) THEN ${encoded} END`;
      }
    }
    return `(${name}::text,${value2})`;
  });
  const projected = pairs.length ? `COALESCE((SELECT jsonb_object_agg(k,v) FROM (VALUES ${pairs.join(",")}) f(k,v) WHERE v IS NOT NULL),'{}'::jsonb)` : `'{}'::jsonb`;
  const selected = param(Array.from(new Set(fields2)));
  return `CASE WHEN t.document_fields IS NULL THEN COALESCE((SELECT jsonb_object_agg(k,v) FROM jsonb_each(${fullDocument}) f(k,v) WHERE k=ANY(${selected}::text[])),'{}'::jsonb) ELSE ${projected} END`;
}
function leanExcludedDocument(collection, excluded, param, full) {
  const known = Array.from(
    /* @__PURE__ */ new Set([
      "_id",
      ...storageFields(collection).map((field) => field.source),
      ...collection === "enil_user" ? ["streakDayList", "subscription", "subscriptionByEnv"] : []
    ])
  );
  const projection = leanDocument(
    collection,
    known.filter((key) => !excluded.includes(key)),
    param,
    full
  );
  const keys = param(excluded);
  return `CASE WHEN t.document_fields IS NULL THEN ${full} - ${keys}::text[] ELSE (${projection}) || ((t.source_document::jsonb) - ${keys}::text[]) END`;
}

// lib/postgres/document-query.ts
var collections = /* @__PURE__ */ new Set([
  ...ORDINARY_COLLECTIONS,
  ...AUTH_COLLECTIONS,
  "enil_runtime_config",
  "enil_subscription_events",
  "enil_user_avatar",
  "enil_push_jobs",
  "enil_push_delivery"
]);
var expressions = /* @__PURE__ */ new WeakMap();
function rememberExpression(value2, expression) {
  if (!value2 || typeof value2 !== "object") throw Error("local_pg_command_shape");
  expressions.set(value2, expression);
  return value2;
}
function documentExpression(collection) {
  if (collection === "enil_user") return "public.user_profile_document(t)";
  return "public.business_document(t)";
}
function decodeDocument(value2, depth = 0) {
  if (depth > 32) throw Error("local_pg_document_depth");
  if (value2 === null || typeof value2 !== "object") return value2;
  if (Array.isArray(value2))
    return value2.map((x) => decodeDocument(x, depth + 1));
  const object = value2;
  if (Object.keys(object).length === 1 && typeof object.__cloudbaseDate === "string") {
    const date2 = new Date(object.__cloudbaseDate);
    if (!Number.isFinite(date2.getTime())) throw Error("local_pg_document_date");
    return date2;
  }
  return Object.fromEntries(
    Object.entries(object).map(([key, item]) => [
      key,
      decodeDocument(item, depth + 1)
    ])
  );
}
function compileDocumentRead(query, count = false, indexed = false, primary = false, currentSchema = false) {
  if (!collections.has(query.collection) || !primary && ["enil_user_avatar", "enil_push_jobs", "enil_push_delivery"].includes(
    query.collection
  ))
    throw Error("local_pg_collection_not_migrated");
  if (!Number.isSafeInteger(query.skip) || query.skip < 0 || query.skip > 1e6 || !Number.isSafeInteger(query.limit) || query.limit < 1 || query.limit > 1e3 || query.order.length > 4)
    throw Error("local_pg_query_budget");
  const values = [];
  const param = (v) => {
    values.push(v);
    return `$${values.length}`;
  };
  const path = (field) => {
    if (field.length > 160 || !/^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$/.test(field))
      throw Error("local_pg_field");
    return "lax $." + field.split(".").map((x) => JSON.stringify(x)).join(".");
  };
  const json = (v) => param(JSON.stringify(sourceJson(v))) + "::jsonb";
  const equality = (value2) => {
    const target = json(value2);
    return `(v = ${target} OR (jsonb_typeof(v)='array' AND v @> jsonb_build_array(${target})))`;
  };
  const fieldCondition = (field, input, document = "d") => {
    const fieldPath = () => param(path(field)) + "::jsonpath";
    const present = () => `jsonb_path_exists(${document},${fieldPath()})`;
    const each = (predicate2) => `EXISTS (SELECT 1 FROM jsonb_path_query(${document},${fieldPath()}) AS x(v) WHERE ${predicate2})`;
    const operator = input && typeof input === "object" ? expressions.get(input) : void 0;
    if (!operator && input && typeof input === "object" && !Array.isArray(input) && !(input instanceof Date) && Object.values(input).some(
      (v) => !!v && typeof v === "object" && expressions.has(v)
    )) {
      return "(" + Object.entries(input).map(([key, v]) => fieldCondition(field + "." + key, v)).join(" AND ") + ")";
    }
    if (!operator)
      return input === null ? `(NOT ${present()} OR ${each(equality(input))})` : each(equality(input));
    const [value2] = operator.values;
    switch (operator.operator) {
      case "and":
      case "or": {
        const clauses = operator.values.length === 1 && Array.isArray(operator.values[0]) ? operator.values[0] : operator.values;
        if (clauses.length > 100) throw Error("local_pg_filter_budget");
        return clauses.length ? "(" + clauses.map((v) => fieldCondition(field, v)).join(operator.operator === "and" ? " AND " : " OR ") + ")" : operator.operator === "and" ? "TRUE" : "FALSE";
      }
      case "eq":
        return fieldCondition(field, value2);
      case "neq":
        return `NOT (${fieldCondition(field, value2)})`;
      case "exists":
        if (typeof value2 !== "boolean") throw Error("local_pg_exists");
        return value2 ? present() : `NOT ${present()}`;
      case "in":
      case "nin": {
        if (!Array.isArray(value2) || value2.length > 1e3)
          throw Error("local_pg_in_budget");
        const test = value2.length ? "(" + value2.map((x) => fieldCondition(field, x)).join(" OR ") + ")" : "FALSE";
        return operator.operator === "in" ? test : `NOT (${test})`;
      }
      case "lt":
      case "lte":
      case "gt":
      case "gte": {
        const op = { lt: "<", lte: "<=", gt: ">", gte: ">=" }[operator.operator];
        const target = json(value2);
        return each(
          `jsonb_typeof(v)=jsonb_typeof(${target}) AND v ${op} ${target}`
        );
      }
      case "regex": {
        const [pattern, flags] = operator.values;
        if (typeof pattern !== "string" || pattern.length > 2048 || !["", "i"].includes(String(flags)))
          throw Error("local_pg_regex");
        return each(
          `jsonb_typeof(v)='string' AND (v #>> '{}') ${flags === "i" ? "~*" : "~"} ${param(pattern)}`
        );
      }
      default:
        throw Error("local_pg_field_operator");
    }
  };
  const condition = (input, depth = 0) => {
    if (depth > 16 || !input || typeof input !== "object" || Array.isArray(input))
      throw Error("local_pg_filter");
    const expression = expressions.get(input);
    if (expression) {
      if (!["and", "or"].includes(expression.operator))
        throw Error("local_pg_filter_operator");
      const clauses = expression.values.length === 1 && Array.isArray(expression.values[0]) ? expression.values[0] : expression.values;
      if (clauses.length > 1e3) throw Error("local_pg_filter_budget");
      return clauses.length ? "(" + clauses.map((x) => condition(x, depth + 1)).join(expression.operator === "and" ? " AND " : " OR ") + ")" : expression.operator === "and" ? "TRUE" : "FALSE";
    }
    const entries = Object.entries(input);
    if (entries.length > 100) throw Error("local_pg_filter_budget");
    return entries.length ? "(" + entries.map(([key, value2]) => fieldCondition(key, value2)).join(" AND ") + ")" : "TRUE";
  };
  const filters2 = query.where.map((x) => condition(x));
  const indexedColumns = {
    enil_auth_user: {
      id: "id",
      email: "email",
      canonicalUserId: "canonicalUserId"
    },
    enil_auth_session: { id: "id", token: "token", userId: "userId" },
    enil_auth_account: {
      id: "id",
      providerId: "providerId",
      accountId: "accountId",
      userId: "userId"
    },
    enil_auth_verification: { id: "id", identifier: "identifier" },
    enil_auth_identity: {
      provider: "provider",
      providerUserId: "provider_user_id",
      canonicalUserId: "canonical_user_id",
      email: "email"
    },
    enil_runtime_config: { key: "config_key" },
    enil_push_jobs: { jobId: "job_id", status: "status" },
    enil_push_delivery: {
      date: "date",
      kind: "kind",
      state: "state",
      tokenId: "token_id"
    },
    enil_push_tokens: { token: "token", userId: "user_id" },
    enil_event_log: { service: "service", level: "level" },
    enil_user: { userId: "user_id" },
    enil_subscription_events: {
      userId: "user_id",
      provider: "provider",
      eventId: "event_id"
    },
    enil_news: { public: "is_public", titleid: "titleid", date: "date_ms" },
    enli_news_translation: { newsId: "news_id", languageCode: "language_code" },
    enli_news_title_translation: {
      newsId: "news_id",
      languageCode: "language_code"
    },
    enil_news_favorite: { userId: "user_id", newsId: "news_id" },
    enil_level_learning_progress: {
      userId: "user_id",
      newsId: "news_id",
      level: "level"
    },
    enil_quiz_answer: { userId: "user_id", newsId: "news_id" },
    enil_vocabulary: { userId: "user_id", newsId: "news_id", word: "word" },
    enil_word_dictionary: { word: "word", languageCode: "language_code" },
    enil_word_tts: { hash_id: "hash_id" }
  };
  const columns = { _id: "_id", ...indexedColumns[query.collection] };
  const prefilter = (input, depth = 0) => {
    if (!input || typeof input !== "object" || depth > 16) return "TRUE";
    const expression = expressions.get(input);
    if (expression && ["and", "or"].includes(expression.operator)) {
      const args = expression.values.length === 1 && Array.isArray(expression.values[0]) ? expression.values[0] : expression.values;
      return args.length ? "(" + args.map((x) => prefilter(x, depth + 1)).join(expression.operator === "and" ? " AND " : " OR ") + ")" : expression.operator === "and" ? "TRUE" : "FALSE";
    }
    return Object.entries(input).map(([key, value2]) => {
      if (query.collection === "enil_user" && [
        "clerkData.primary_email_address",
        "clerkData.verified_email_addresses"
      ].includes(key) && value2 && typeof value2 === "object" && expressions.get(value2)?.operator === "regex")
        return fieldCondition(
          key.slice("clerkData.".length),
          value2,
          "t.clerk_data"
        );
      if (!Object.hasOwn(columns, key)) return "TRUE";
      const baseColumn = `t."${columns[key]}"`;
      const col = key !== "_id" && ["enil_push_jobs", "enil_push_delivery"].includes(query.collection) ? `COALESCE(${baseColumn},t.source_document->>'${key}')` : baseColumn;
      const expr = value2 && typeof value2 === "object" ? expressions.get(value2) : void 0;
      if (expr) {
        if (["enil_auth_user", "enil_auth_identity"].includes(
          query.collection
        ) && key === "email" && expr.operator === "regex") {
          const [pattern, flags] = expr.values;
          return `${col} ${flags === "i" ? "~*" : "~"} ${param(pattern)}`;
        }
        if (expr.operator === "in" && Array.isArray(expr.values[0])) {
          const list = expr.values[0];
          const kind = query.collection === "enil_news" && key === "public" ? "boolean" : key === "date" || key === "level" ? "number" : "string";
          if (list.every((value3) => value3 === null || typeof value3 === kind)) {
            const nonNull = list.filter((value3) => value3 !== null);
            const match = nonNull.length ? `${col} IN (${nonNull.map((value3) => param(value3)).join(",")})` : "FALSE";
            return list.includes(null) ? `(${match} OR ${col} IS NULL)` : match;
          }
        }
        if (query.collection === "enil_word_dictionary" && key === "word" && expr.operator === "in") {
          const words = expr.values[0];
          if (Array.isArray(words) && words.every((word) => typeof word === "string"))
            return words.length ? `${col} IN (${words.map((word) => param(word)).join(",")})` : "FALSE";
        }
        if (["lt", "lte", "gt", "gte"].includes(expr.operator) && typeof expr.values[0] === "number")
          return `${col} ${{ lt: "<", lte: "<=", gt: ">", gte: ">=" }[expr.operator]} ${param(expr.values[0])}`;
        return "TRUE";
      }
      if (value2 === null) return `${col} IS NULL`;
      return ["string", "number", "boolean"].includes(typeof value2) ? `${col}=${param(value2)}` : "TRUE";
    }).join(" AND ") || "TRUE";
  };
  const earlyFilters = indexed ? query.where.map((x) => prefilter(x)) : [];
  if (query.id !== void 0) {
    if (!query.id || query.id.length > 512) throw Error("local_pg_document_id");
    filters2.push(`d->>'_id'=${param(query.id)}`);
    if (indexed) earlyFilters.push(`t._id=${param(query.id)}`);
  }
  const where = filters2.length ? filters2.join(" AND ") : "TRUE";
  const sortColumns = {
    enil_news: {
      date: "date_ms",
      readCount: "read_count",
      updatedAt: "updated_at_ms"
    },
    enil_user: {
      level: "level",
      newsRead: "news_read",
      wordsRead: "words_read",
      minutesRead: "minutes_read"
    }
  };
  const typedSort = [];
  const order = (count ? [] : query.order).flatMap(
    ([field, direction], index) => {
      if (!["asc", "desc"].includes(direction)) throw Error("local_pg_order");
      path(field);
      const column = indexed && sortColumns[query.collection]?.[field];
      const suffix = `${direction.toUpperCase()} NULLS ${direction === "asc" ? "FIRST" : "LAST"}`;
      if (column) {
        typedSort.push(`t."${column}" AS sort_${index}`);
        return [
          `sort_${index} ${suffix}`,
          `(d ? ${param(field)}) ${direction.toUpperCase()}`
        ];
      }
      return [
        `jsonb_path_query_first(d,${param(path(field))}::jsonpath) ${suffix}`
      ];
    }
  );
  if (!count) order.push(`d->>'_id' ASC`);
  let selected = "d";
  if (!count && query.fields && !(currentSchema && indexed && primary)) {
    if (Object.keys(query.fields).some((key) => key.includes(".")))
      throw Error("local_pg_projection_nested_unsupported");
    const included = Object.entries(query.fields).filter(([key, value2]) => key !== "_id" && value2).map(([key]) => key);
    if (included.length) {
      if (query.fields._id !== false) included.push("_id");
      selected = `COALESCE((SELECT jsonb_object_agg(k,v) FROM jsonb_each(d) e(k,v) WHERE k=ANY(${param(included)}::text[])),'{}'::jsonb) AS d`;
    } else {
      selected = `d - ${param(Object.keys(query.fields).filter((key) => query.fields[key] === false))}::text[] AS d`;
    }
  }
  if (currentSchema && indexed && primary) {
    const needed = /* @__PURE__ */ new Set(["_id"]);
    const collect = (input) => {
      if (!input || typeof input !== "object") return;
      const expression = expressions.get(input);
      if (expression && ["and", "or"].includes(expression.operator)) {
        for (const value2 of expression.values)
          for (const item of Array.isArray(value2) ? value2 : [value2])
            collect(item);
      } else for (const key of Object.keys(input)) needed.add(key.split(".")[0]);
    };
    query.where.forEach(collect);
    if (!count)
      query.order.forEach(([field]) => needed.add(field.split(".")[0]));
    const full = documentExpression(query.collection);
    const skinny = leanDocument(
      query.collection,
      Array.from(needed),
      param,
      full
    );
    const nativeOrder = count ? [] : order.map(
      (item) => item === `d->>'_id' ASC` ? "physical_id ASC" : item
    );
    if (count)
      return {
        sql: `WITH documents AS (SELECT ${skinny} AS d FROM public.${query.collection} t WHERE ${earlyFilters.length ? earlyFilters.join(" AND ") : "TRUE"}) SELECT count(*)::text AS total FROM documents WHERE ${where}`,
        values
      };
    let output = full;
    if (query.fields) {
      if (Object.keys(query.fields).some((key) => key.includes(".")))
        throw Error("local_pg_projection_nested_unsupported");
      const included = Object.entries(query.fields).filter(([key, value2]) => key !== "_id" && value2).map(([key]) => key);
      if (included.length) {
        if (query.fields._id !== false) included.push("_id");
        output = leanDocument(query.collection, included, param, full);
      } else {
        const excluded = Object.keys(query.fields).filter(
          (key) => query.fields[key] === false
        );
        output = excluded.length ? leanExcludedDocument(query.collection, excluded, param, full) : full;
      }
    }
    const sorting = nativeOrder.join(",");
    return {
      sql: `WITH documents AS (SELECT t._id AS physical_id,${skinny} AS d${typedSort.length ? "," + typedSort.join(",") : ""} FROM public.${query.collection} t WHERE ${earlyFilters.length ? earlyFilters.join(" AND ") : "TRUE"}), page AS MATERIALIZED (SELECT physical_id,row_number() OVER (ORDER BY ${sorting}) AS ordinal FROM documents WHERE ${where} ORDER BY ${sorting} LIMIT ${param(query.limit)} OFFSET ${param(query.skip)}) SELECT ${output} AS d FROM page p JOIN public.${query.collection} t ON t._id=p.physical_id ORDER BY p.ordinal`,
      values
    };
  }
  const sql = `WITH documents AS (SELECT ${documentExpression(query.collection)} AS d${typedSort.length ? "," + typedSort.join(",") : ""} FROM public.${query.collection} t WHERE ${earlyFilters.length ? earlyFilters.join(" AND ") : "TRUE"}) SELECT ${count ? "count(*)::text AS total" : selected} FROM documents WHERE ${where}${count ? "" : ` ORDER BY ${order.join(",")} LIMIT ${param(query.limit)} OFFSET ${param(query.skip)}`}`;
  return { sql, values };
}
function selectFields(document, fields2) {
  if (!fields2) return document;
  if (Object.keys(fields2).some((key) => key.includes(".")))
    throw Error("local_pg_projection_nested_unsupported");
  const included = Object.entries(fields2).filter(([key, value2]) => key !== "_id" && value2).map(([key]) => key);
  if (included.length)
    return Object.fromEntries(
      ["_id", ...included].filter((key) => fields2[key] !== false && Object.hasOwn(document, key)).map((key) => [key, document[key]])
    );
  return Object.fromEntries(
    Object.entries(document).filter(([key]) => fields2[key] !== false)
  );
}

// lib/db/pg-primary.ts
var mutations = /* @__PURE__ */ new WeakMap();
var allowed = /* @__PURE__ */ new Set([
  ...DOCUMENT_COLLECTIONS,
  "enil_subscription_events",
  "enil_user_avatar",
  "enil_push_jobs",
  "enil_push_delivery"
]);
function commandObject(operation, value2) {
  const object = Object.freeze({});
  mutations.set(object, { operation, value: value2 });
  return object;
}
function predicate(operator, values) {
  const value2 = {};
  Object.defineProperties(value2, {
    and: { value: (other) => predicate("and", [value2, other]) },
    or: { value: (other) => predicate("or", [value2, other]) }
  });
  return rememberExpression(value2, { operator, values });
}
var filters = [
  "eq",
  "neq",
  "lt",
  "lte",
  "gt",
  "gte",
  "in",
  "nin",
  "exists",
  "and",
  "or"
];
var primaryCommand = Object.fromEntries([
  ...filters.map((operator) => [
    operator,
    (...values) => predicate(operator, values)
  ]),
  ...["inc", "remove", "set"].map((operator) => [
    operator,
    (value2) => commandObject(operator, value2)
  ])
]);
function clone(value2) {
  return decodeDocument(sourceJson(value2));
}
function merge(base, fields2) {
  const next = clone(base);
  for (const [path, value2] of Object.entries(fields2)) {
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$/.test(path) || path.split(".").some((x) => ["__proto__", "prototype", "constructor"].includes(x)))
      throw Error("pg_primary_update_field");
    if (path === "_id") {
      if (value2 !== base._id) throw Error("pg_primary_id_immutable");
      continue;
    }
    const parts = path.split("."), key = parts.pop();
    let target = next;
    for (const part of parts) {
      if (target[part] == null) target[part] = {};
      if (typeof target[part] !== "object" || Array.isArray(target[part]))
        throw Error("pg_primary_update_path");
      target = target[part];
    }
    const operation = value2 && typeof value2 === "object" ? mutations.get(value2) : void 0;
    if (operation?.operation === "remove") delete target[key];
    else if (operation?.operation === "inc") {
      const current = target[key] ?? 0;
      if (typeof current !== "number" || typeof operation.value !== "number" || !Number.isFinite(current + operation.value))
        throw Error("pg_primary_increment");
      target[key] = current + operation.value;
    } else if (operation?.operation === "set")
      target[key] = clone(operation.value);
    else if (value2 && typeof value2 === "object" && !Array.isArray(value2) && !(value2 instanceof Date))
      target[key] = merge(target[key] ?? {}, value2);
    else if (value2 !== void 0) target[key] = clone(value2);
  }
  return next;
}
function createPrimaryDatabase(pool, options = {}) {
  const context = new import_node_async_hooks.AsyncLocalStorage();
  const session = (client, check = () => {
  }, readOnlySession = false) => {
    const execute = async (sql, values = []) => {
      check();
      return client ? client.query(sql, values) : pool.query(sql, values);
    };
    const lockedDocuments = /* @__PURE__ */ new Set();
    const lockKeys = async (keys = []) => {
      if (!client || readOnlySession)
        throw Error("pg_primary_write_transaction_required");
      for (const key of [
        ...Array.from(
          new Set(
            keys.map((key2) => JSON.stringify(["levelread-key-v1", ...key2]))
          )
        )
      ].sort())
        await execute("SELECT pg_advisory_xact_lock(hashtextextended($1,0))", [
          key
        ]);
    };
    const lockDocument = async (collection, id) => {
      if (!client || readOnlySession || !allowed.has(collection))
        throw Error("pg_primary_write_transaction_required");
      const key = JSON.stringify([collection, id]);
      if (lockedDocuments.has(key)) return;
      const sql = "SELECT _id FROM public." + collection + " WHERE _id=$1 FOR UPDATE";
      if ((await execute(sql, [id])).rowCount === 0) {
        await execute("SELECT pg_advisory_xact_lock(hashtextextended($1,0))", [
          key
        ]);
        await execute(sql, [id]);
      }
      lockedDocuments.add(key);
    };
    const rows = async (query, count = false) => {
      if (!client && context.getStore())
        return context.getStore().select(query, count);
      if (client && !readOnlySession && query.id !== void 0)
        await lockDocument(query.collection, query.id);
      if (client && !readOnlySession && query.collection === "enil_subscription_events") {
        for (const clause of query.where) {
          const event = clause;
          if (typeof event?.provider === "string" && typeof event?.eventId === "string")
            await lockKeys([
              ["subscription-event", event.provider, event.eventId]
            ]);
        }
      }
      const compiled = compileDocumentRead(
        query,
        count,
        true,
        true,
        options.currentSchema === true
      );
      let result = await execute(compiled.sql, compiled.values);
      if (client && !readOnlySession && !count && query.id === void 0 && ["enil_auth_user", "enil_auth_session"].includes(query.collection)) {
        const ids = result.rows.map((row) => decodeDocument(row.d)._id).sort();
        for (const id of ids) await lockDocument(query.collection, id);
        if (ids.length) result = await execute(compiled.sql, compiled.values);
      }
      return count ? result.rows : result.rows.map((row) => decodeDocument(row.d));
    };
    const runTransaction = async (work, readOnly = false, keys = []) => {
      if (client) {
        check();
        if (keys.length) await lockKeys(keys);
        return work(database);
      }
      if (context.getStore())
        return context.getStore().runTransaction(work, { keys });
      const connection = await pool.connect();
      let alive = true, destroy = false;
      const onError = () => {
        alive = false;
        destroy = true;
      };
      connection.on("error", onError);
      const assertActive = () => {
        if (!alive) throw Error("pg_primary_transaction_closed");
      };
      try {
        await connection.query(
          readOnly ? "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY" : "BEGIN"
        );
        await connection.query(
          "SET LOCAL statement_timeout='10s'; SET LOCAL lock_timeout='10s'; SET LOCAL idle_in_transaction_session_timeout='15s'"
        );
        if (!readOnly)
          await connection.query(
            "SELECT set_config('levelread.business_write','true',true)"
          );
        const transaction = session(connection, assertActive, readOnly);
        const result = await context.run(
          transaction,
          () => transaction.runTransaction(work, { keys })
        );
        assertActive();
        const committed = await connection.query("COMMIT");
        if (committed.command !== "COMMIT")
          throw Error("pg_primary_transaction_not_committed");
        return result;
      } catch (error) {
        destroy = true;
        throw error;
      } finally {
        alive = false;
        connection.release(destroy);
        connection.removeListener("error", onError);
      }
    };
    const write = async (collection, document, deleting = false) => {
      check();
      if (!allowed.has(collection)) throw Error("pg_primary_collection_scope");
      if (!client) throw Error("pg_primary_transaction_required");
      const id = document._id;
      if (typeof id !== "string" || !id || id.length > 512)
        throw Error("pg_primary_document_id");
      await lockDocument(collection, id);
      const identities = {
        enil_user: [["userId"]],
        enil_news: [["titleid"]],
        enil_runtime_config: [["key"]],
        enil_level_learning_progress: [["userId", "newsId", "level"]],
        enil_quiz_answer: [["userId", "newsId"]],
        enil_auth_user: [["id"], ["email"]],
        enil_auth_session: [["id"], ["token"]],
        enil_auth_account: [["id"], ["providerId", "accountId"]],
        enil_auth_verification: [["id"]],
        enil_subscription_events: [["provider", "eventId"]]
      };
      if (!deleting)
        for (const keys of identities[collection] ?? []) {
          if (keys.some((key) => document[key] == null)) continue;
          const where = Object.fromEntries(
            keys.map((key) => [key, document[key]])
          );
          if (collection === "enil_auth_user" && keys[0] === "email")
            where.email = predicate("regex", [
              "^" + String(document.email).replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "$",
              "i"
            ]);
          where._id = primaryCommand.neq(id);
          if ((await rows({
            collection,
            where: [where],
            order: [],
            skip: 0,
            limit: 1
          })).length)
            throw Error("pg_primary_logical_identity_conflict");
        }
      const operational = ["enil_push_jobs", "enil_push_delivery"].includes(
        collection
      );
      const generic = collection === "enil_user_avatar" || operational;
      if (deleting)
        await execute(`DELETE FROM public.${collection} WHERE _id=$1`, [id]);
      else {
        const previous = (await rows({
          collection,
          id,
          where: [],
          order: [],
          skip: 0,
          limit: 1
        }))[0];
        if (previous && [
          "enil_user",
          "enil_user_avatar",
          "enil_vocabulary",
          "enil_quiz_answer",
          "enil_level_learning_progress",
          "enil_news_favorite",
          "enil_subscription_events"
        ].includes(collection) && previous.userId !== document.userId)
          throw Error("pg_primary_ownership");
        const immutable = {
          enil_auth_identity: ["provider", "providerUserId", "canonicalUserId"],
          enil_auth_user: ["id", "canonicalUserId"],
          enil_auth_session: ["id", "userId"],
          enil_auth_account: ["id", "userId", "providerId", "accountId"],
          enil_auth_verification: ["id", "identifier"]
        };
        for (const field of immutable[collection] ?? [])
          if (previous?.[field] != null && previous[field] !== document[field])
            throw Error("pg_primary_identity_ownership");
        if (generic && !operational) {
          const raw = JSON.stringify(sourceJson(document));
          const written = await execute(
            `INSERT INTO public.enil_user_avatar (_id,user_id,revision,source_document) VALUES ($1,$2,$3,$4::jsonb)
            ON CONFLICT (_id) DO UPDATE SET revision=EXCLUDED.revision,source_document=EXCLUDED.source_document,document_fields=EXCLUDED.document_fields WHERE enil_user_avatar.user_id=EXCLUDED.user_id`,
            [id, document.userId, document.revision, raw]
          );
          if (written.rowCount !== 1) throw Error("pg_primary_ownership");
        } else {
          const mapped = collection === "enil_subscription_events" ? eventProjection(id, document.userId, document) : projectDocument(
            {
              collection,
              sourceId: id,
              ownerId: document.userId
            },
            document,
            previous
          );
          if ((await execute(mapped.sql, mapped.values)).rowCount !== 1)
            throw Error("pg_primary_ownership");
          if (collection === "enil_user")
            await execute("SELECT public.write_user_relations($1,$2::jsonb)", [
              id,
              JSON.stringify(sourceJson(document))
            ]);
        }
      }
    };
    const chain = (query) => {
      const next = (patch) => chain({ ...query, ...patch });
      const get = async () => {
        const data = (await rows(query)).map(
          (row) => selectFields(row, query.fields)
        );
        return { data: query.id === void 0 ? data : data[0] ?? null };
      };
      return {
        where: (where) => next({ where: [...query.where, where] }),
        orderBy: (field, direction) => next({ order: [...query.order, [field, direction]] }),
        skip: (skip) => next({ skip }),
        limit: (limit) => next({ limit }),
        field: (fields2) => next({ fields: fields2 }),
        doc: (id) => next({ id }),
        get,
        count: async () => ({
          total: Number((await rows(query, true))[0].total)
        }),
        add: async (fields2) => {
          if (query.id !== void 0) throw Error("pg_primary_add_query");
          const id = fields2._id ?? (0, import_node_crypto3.randomUUID)();
          const cacheKeys = {
            enil_news_favorite: ["userId", "newsId"],
            enli_news_translation: ["newsId", "languageCode"],
            enli_news_title_translation: ["newsId", "languageCode"],
            enil_word_dictionary: ["word", "languageCode"],
            enil_word_tts: ["hash_id"]
          };
          const logical = cacheKeys[query.collection];
          const keys = logical?.every((key) => fields2[key] != null) ? [[query.collection, ...logical.map((key) => fields2[key])]] : [];
          return runTransaction(
            async (tx) => {
              if ((await tx.collection(query.collection).doc(id).get()).data)
                throw Error("pg_primary_duplicate_id");
              const cacheKeys2 = {
                enil_news_favorite: ["userId", "newsId"],
                enli_news_translation: ["newsId", "languageCode"],
                enli_news_title_translation: ["newsId", "languageCode"],
                enil_word_dictionary: ["word", "languageCode"],
                enil_word_tts: ["hash_id"]
              };
              const keys2 = cacheKeys2[query.collection];
              if (keys2 && keys2.every((key) => fields2[key] != null)) {
                const existing = await tx.collection(query.collection).where(
                  Object.fromEntries(keys2.map((key) => [key, fields2[key]]))
                ).limit(2).get();
                if (existing.data.length > 1)
                  throw Error("pg_primary_logical_key_ambiguous");
                if (existing.data[0]) return { id: existing.data[0]._id };
              }
              await tx.persist(query.collection, { ...fields2, _id: id });
              return { id };
            },
            false,
            keys
          );
        },
        set: async (fields2) => {
          if (!query.id || fields2._id !== void 0 && fields2._id !== query.id)
            throw Error("pg_primary_set_id");
          return runTransaction(async (tx) => {
            await tx.persist(query.collection, { ...fields2, _id: query.id });
            return { id: query.id, updated: 1 };
          });
        },
        update: async (fields2) => mutate(false, fields2),
        remove: async () => mutate(true)
      };
      async function mutate(deleting, fields2) {
        const increment = fields2?.readCount && typeof fields2.readCount === "object" ? mutations.get(fields2.readCount) : void 0;
        if (!deleting && query.collection === "enil_news" && query.id && !query.where.length && increment?.operation === "inc" && Number.isSafeInteger(increment.value) && Object.keys(fields2).every(
          (key) => key === "readCount" || key === "updatedAt"
        ) && (fields2.updatedAt === void 0 || Number.isSafeInteger(fields2.updatedAt)))
          return runTransaction(
            (tx) => tx.incrementNewsReadCount(
              query.id,
              increment.value,
              fields2.updatedAt
            )
          );
        return runTransaction(async (tx) => {
          const selected = [];
          for (let offset = 0; ; offset += 500) {
            const page = await tx.select({
              ...query,
              fields: void 0,
              order: [["_id", "asc"]],
              skip: offset,
              limit: 500
            });
            selected.push(...page);
            if (page.length < 500) break;
            if (selected.length >= 1e5)
              throw Error("pg_primary_mutation_budget");
          }
          let changed = 0;
          for (const row of selected) {
            const current = (await tx.select({
              ...query,
              id: row._id,
              fields: void 0,
              skip: 0,
              limit: 1
            }))[0];
            if (!current) continue;
            await tx.persist(
              query.collection,
              deleting ? current : merge(current, fields2),
              deleting
            );
            changed++;
          }
          return deleting ? { deleted: changed } : { updated: changed };
        });
      }
    };
    const database = {
      command: primaryCommand,
      RegExp: ({
        regexp,
        options: options2 = ""
      }) => predicate("regex", [regexp, options2]),
      collection(collection) {
        if (!allowed.has(collection)) throw Error("pg_primary_collection_scope");
        return chain({ collection, where: [], order: [], skip: 0, limit: 100 });
      },
      runTransaction: (work, options2 = {}) => runTransaction(work, false, options2.keys),
      runReadTransaction: (work) => runTransaction(work, true),
      async incrementNewsReadCount(id, delta, updatedAt) {
        check();
        if (!client) throw Error("pg_primary_transaction_required");
        if (!id || id.length > 512) throw Error("pg_primary_document_id");
        const result = await execute(
          `UPDATE public.enil_news t SET
          read_count=COALESCE(t.read_count,0)+$2::bigint,
          updated_at_ms=CASE WHEN $4::bigint IS NULL THEN t.updated_at_ms ELSE $4::bigint END,
          source_document=jsonb_set(${documentExpression("enil_news")},'{readCount}',to_jsonb(COALESCE(t.read_count,0)+$2::bigint),true)||$3::jsonb
          WHERE t._id=$1 RETURNING read_count`,
          [
            id,
            delta,
            JSON.stringify(updatedAt === void 0 ? {} : { updatedAt }),
            updatedAt ?? null
          ]
        );
        if (result.rows.some(
          (row) => !Number.isSafeInteger(Number(row.read_count))
        ))
          throw Error("pg_primary_increment");
        return { updated: result.rowCount ?? 0 };
      },
      // Internal operations are available only on the transaction-bound object.
      select: rows,
      persist: write
    };
    return database;
  };
  return session();
}

// scripts/pg-primary-ingest.ts
var languages = ["zh-CN", "zh-TW", "ja", "ko", "es", "pt-BR"];
function stable(value2) {
  return Array.isArray(value2) ? value2.map(stable) : value2 && typeof value2 === "object" ? Object.fromEntries(Object.keys(value2).sort().map((k) => [k, stable(value2[k])])) : value2;
}
async function ingest(database, request) {
  const { package: news, titleTranslations: titles, bodyTranslations: bodies } = request;
  if (!news || news.public !== false || typeof news.titleid !== "string" || !/^[a-z0-9][a-z0-9-]{0,199}$/.test(news.titleid) || !Array.isArray(titles) || !Array.isArray(bodies)) throw Error("ingest_scope");
  for (const rows of [titles, bodies]) if (rows.length !== 6 || languages.some((l) => rows.filter((r) => r.languageCode === l).length !== 1)) throw Error("ingest_languages");
  const digest = (0, import_node_crypto4.createHash)("sha256").update(JSON.stringify(stable({ news, titles, bodies }))).digest("hex");
  const id = "news-" + (0, import_node_crypto4.createHash)("sha256").update(news.titleid).digest("hex"), now = Date.now();
  const titleIds = languages.map((l) => id + "-title-" + l), bodyIds = languages.map((l) => id + "-body-" + l);
  return database.runTransaction(async (tx) => {
    await tx.collection("enil_news").doc(id).get();
    const existing = (await tx.collection("enil_news").where({ titleid: news.titleid }).limit(2).get()).data;
    if (existing.length) {
      if (existing.length !== 1 || existing[0]._id !== id || existing[0].ingestDigest !== digest) throw Error("ingest_titleid_conflict");
      for (let i = 0; i < 6; i++) for (const [collection, ids] of [["enli_news_title_translation", titleIds], ["enli_news_translation", bodyIds]]) {
        const record = (await tx.collection(collection).doc(ids[i]).get()).data;
        if (!record || record.newsId !== id || record.languageCode !== languages[i]) throw Error("ingest_receipt_incomplete");
      }
      return { ok: true, status: "ingested", id, titleTranslationIds: titleIds, bodyTranslationIds: bodyIds, total: 13, reused: true };
    }
    if ((await tx.collection("enil_news").doc(id).get()).data) throw Error("ingest_titleid_conflict");
    for (let i = 0; i < 6; i++) for (const [collection, ids] of [["enli_news_title_translation", titleIds], ["enli_news_translation", bodyIds]]) {
      if ((await tx.collection(collection).doc(ids[i]).get()).data) throw Error("ingest_titleid_conflict");
      if ((await tx.collection(collection).where({ newsId: id, languageCode: languages[i] }).limit(1).get()).data.length) throw Error("ingest_titleid_conflict");
    }
    await tx.collection("enil_news").doc(id).set({ ...news, ingestDigest: digest });
    for (let i = 0; i < 6; i++) {
      const title = titles.find((r) => r.languageCode === languages[i]);
      const body = bodies.find((r) => r.languageCode === languages[i]);
      await tx.collection("enli_news_title_translation").doc(titleIds[i]).set({ ...title, newsId: id, status: "READY", provider: "codex", version: "v1", createdAt: now, updatedAt: now });
      await tx.collection("enli_news_translation").doc(bodyIds[i]).set({ ...body, newsId: id });
    }
    return { ok: true, status: "ingested", id, titleTranslationIds: titleIds, bodyTranslationIds: bodyIds, total: 13, reused: false };
  });
}
async function run(request) {
  const pool = new import_pg2.Pool({ ...poolOptions(), application_name: "levelread-production-primary" });
  const db = createPrimaryDatabase(pool);
  try {
    if (request.action === "check") {
      await db.runReadTransaction(async () => {
      });
      return { ok: true, status: "ready" };
    }
    if (request.action !== "ingest") throw Error("ingest_action");
    return await ingest(db, request);
  } catch (error) {
    return { ok: false, status: error.message === "ingest_titleid_conflict" ? "conflict" : "unavailable" };
  } finally {
    await pool.end();
  }
}
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  createPrimaryDatabase,
  ingest,
  run
});
