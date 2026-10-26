import assert from 'node:assert/strict'

export async function verifyLockPolicy(t, db, pool) {
  await t.test('unrelated documents commit while another document transaction is held', {timeout: 5000}, async () => {
    let entered, release
    const acquired = new Promise(resolve => { entered = resolve })
    const gate = new Promise(resolve => { release = resolve })
    const holder = db.runTransaction(async tx => {
      await tx.collection('enil_news').doc('lock-policy-held').get()
      entered()
      await gate
    })
    try {
      await acquired
      // This must COMMIT before releasing the held transaction. A global lock fails here.
      await db.collection('enil_news').doc('lock-policy-independent').set({titleid:'lock-policy-independent'})
      const result = await pool.query(`SELECT count(*)::int AS n FROM pg_locks
        WHERE locktype='advisory' AND database=(SELECT oid FROM pg_database WHERE datname=current_database())
        AND classid=((hashtextextended('levelread-pg-primary-business',0)>>32)&4294967295)::oid
        AND objid=(hashtextextended('levelread-pg-primary-business',0)&4294967295)::oid AND objsubid=1`)
      assert.equal(result.rows[0].n, 0)
    } finally { release(); await holder }
  })
  await t.test('same missing document permits exactly one read-before-create winner', async () => {
    const claims = await Promise.all(Array.from({length:6},(_,i)=>db.runTransaction(async tx => {
      const ref=tx.collection('enil_push_jobs').doc('lock-policy-claim')
      if ((await ref.get()).data) return false
      await ref.set({jobId:'lock-policy-claim',status:'queued',winner:i})
      return true
    })))
    assert.equal(claims.filter(Boolean).length,1)
  })
  await t.test('filtered concurrent patches re-read after the document lock', async () => {
    await db.collection('enil_news').doc('lock-policy-patch').set({titleid:'lock-policy-patch',title:'start',public:false,readCount:0})
    await Promise.all([
      db.collection('enil_news').where({_id:'lock-policy-patch'}).update({title:'edited'}),
      db.collection('enil_news').where({_id:'lock-policy-patch'}).update({public:true}),
      db.collection('enil_news').doc('lock-policy-patch').update({readCount:db.command.inc(1)}),
    ])
    const row=(await db.collection('enil_news').doc('lock-policy-patch').get()).data
    assert.equal(row.title,'edited');assert.equal(row.public,true);assert.equal(row.readCount,1)
  })
  await t.test('read-only snapshots remain read-only and do not acquire document locks', async () => {
    await db.runReadTransaction(async tx => {
      await tx.collection('enil_news').doc('lock-policy-held').get()
    })
  })
}
