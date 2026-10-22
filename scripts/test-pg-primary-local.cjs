#!/usr/bin/env node
const fs = require('node:fs'),
  path = require('node:path'),
  os = require('node:os')
const { spawnSync } = require('node:child_process')
const root = path.resolve(__dirname, '..'),
  directory = fs.mkdtempSync(
    path.join(os.tmpdir(), 'levelread-pg-services-test.'),
  )
const data = path.join(directory, 'data'),
  user = os.userInfo().username,
  env = { ...process.env, NODE_ENV: 'test' }
for (const key of Object.keys(env))
  if (/^(PG|CLOUDBASE_)/.test(key) || key === 'DATABASE_URL') delete env[key]
let started = false
function run(binary, args, stdio = 'pipe') {
  const result = spawnSync(binary, args, {
    cwd: root,
    env,
    stdio,
    encoding: 'utf8',
  })
  if (result.status !== 0)
    throw Error(`Local fixture command failed: ${binary}`)
}
try {
  run('initdb', [
    '-D',
    data,
    '-U',
    user,
    '--auth-local=trust',
    '--auth-host=reject',
    '--no-locale',
    '-E',
    'UTF8',
  ])
  run('pg_ctl', [
    '-D',
    data,
    '-l',
    path.join(directory, 'server.log'),
    '-o',
    `-k ${directory} -p 55449 -h ""`,
    '-w',
    'start',
  ])
  started = true
  run('createdb', [
    '-h',
    directory,
    '-p',
    '55449',
    '-U',
    user,
    'pg_primary_test',
  ])
  env.PG_PRIMARY_TEST_SOCKET = directory
  env.PGUSER = user
  run(
    process.execPath,
    [
      '--experimental-test-module-mocks',
      '--test',
      'test/pg-primary.test.mjs',
    ],
    'inherit',
  )
} catch (error) {
  console.error(error.message)
  process.exitCode = 1
} finally {
  if (started) {
    const result = spawnSync(
      'pg_ctl',
      ['-D', data, '-m', 'fast', '-w', 'stop'],
      { env, stdio: 'pipe' },
    )
    if (result.status !== 0) {
      console.error('Fixture stop failed; retained directory')
      process.exitCode = 1
    } else fs.rmSync(directory, { recursive: true })
  } else fs.rmSync(directory, { recursive: true })
}
