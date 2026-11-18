'use strict';

const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const provenance = require('./pg-primary-provenance.json');

const artifacts = {
  sourceSha256: 'scripts/pg-primary-ingest.ts',
  outputSha256: 'scripts/pg-primary-runtime.cjs',
  schemaSha256: 'test/primary-schema.sql',
};

for (const [key, file] of Object.entries(artifacts)) {
  const bytes = readFileSync(resolve(__dirname, '..', file));
  const actual = createHash('sha256').update(bytes).digest('hex');
  assert.equal(actual, provenance[key], `PG provenance mismatch for ${file}`);
}
console.log('PG source, runtime and schema match the recorded SHA-256 hashes.');
