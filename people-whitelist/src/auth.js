import { OAuth2Client } from 'google-auth-library';

const oauthClient = () =>
  new OAuth2Client(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    process.env.GOOGLE_REDIRECT_URI
  );

export async function bootstrapAdmin(pool) {
  const { rows } = await pool.query('select count(*)::int as count from people');
  if (rows[0].count > 0) return;

  const email = (process.env.BOOTSTRAP_ADMIN_EMAIL || '').trim().toLowerCase();
  if (!email) throw new Error('BOOTSTRAP_ADMIN_EMAIL is required for first setup');

  await pool.query(
    `insert into people (person_email, admin, status)
     values ($1, true, 'allowed')
     on conflict (person_email) do nothing`,
    [email]
  );
}

export async function verifyGoogleToken(idToken) {
  const client = oauthClient();
  const ticket = await client.verifyIdToken({
    idToken,
    audience: process.env.GOOGLE_CLIENT_ID,
  });
  return ticket.getPayload();
}

export async function isAdmin(pool, email) {
  const { rows } = await pool.query(
    'select 1 from people where person_email = $1 and admin = true limit 1',
    [email.toLowerCase()]
  );
  return rows.length > 0;
}
