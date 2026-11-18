'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

let poolOptions;
const queries = [];
class Pool {
  constructor(options) {
    poolOptions = options;
  }

  async connect() {
    return {
      on() {},
      removeListener() {},
      release() {},
      async query(sql) {
        queries.push(sql);
        return { rows: [], command: sql };
      },
    };
  }

  async end() {}
}

const mod = { exports: {} };
const databaseUrl = 'postgresql://test:unused@invalid/levelread_prod';
const env = { DATABASE_URL: databaseUrl, PG_SSL_CA_FILE: 'unused' };
const sandbox = {
  URL,
  module: mod,
  exports: mod.exports,
  process: { env },
  console,
  require(name) {
    if (name === 'pg') return { Pool };
    if (name === 'node:fs') return { readFileSync: () => '-----BEGIN CERTIFICATE-----' };
    return require(name);
  },
};
const runtime = path.join(__dirname, 'scripts/pg-primary-runtime.cjs');
vm.runInNewContext(fs.readFileSync(runtime, 'utf8'), sandbox);
const { run, createPrimaryDatabase } = mod.exports;

async function testRuntime() {
  assert.equal((await run({ action: 'check' })).status, 'ready');
  assert.equal(poolOptions.ssl.rejectUnauthorized, true);
  assert.equal(typeof poolOptions.ssl.checkServerIdentity, 'function');
  assert(queries.includes('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY'));
  assert(!queries.some(sql => sql.includes('levelread.business_write')));

  const database = createPrimaryDatabase(new Pool({}));
  await assert.rejects(database.runReadTransaction(tx => tx.collection('unrelated_table')), /pg_primary_collection_scope/);
  await assert.rejects(
    database.runReadTransaction(tx => tx.collection('enil_news').doc('test-id').set({ titleid: 'test-id' })),
    /pg_primary_write_transaction_required/,
  );

  env.DATABASE_URL = 'postgresql://test:unused@invalid/other';
  await assert.rejects(run({ action: 'check' }), /configuration/);
  env.DATABASE_URL = databaseUrl + '?sslmode=disable';
  await assert.rejects(run({ action: 'check' }), /configuration/);
  console.log('PG runtime passed verified TLS, configuration checks and read-only scope.');
}

testRuntime().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
