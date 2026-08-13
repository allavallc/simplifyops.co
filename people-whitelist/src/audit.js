export async function logAudit(pool, { actorEmail, action, subjectEmail, oldValue, newValue }) {
  await pool.query(
    `insert into audit_log (actor_email, action, subject_email, old_value, new_value)
     values ($1, $2, $3, $4, $5)`,
    [actorEmail || null, action, subjectEmail || null, oldValue || null, newValue || null]
  );
}
