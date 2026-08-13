export async function isWhitelisted(pool, email) {
  const { rows } = await pool.query(
    "select 1 from whitelist_entries where person_email = $1 and status = 'allowed' limit 1",
    [email.toLowerCase()]
  );
  return rows.length > 0;
}
