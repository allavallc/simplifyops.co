import express from 'express';
import fs from 'node:fs';
import path from 'node:path';
import { OAuth2Client } from 'google-auth-library';
import multer from 'multer';
import { logAudit } from '../audit.js';
import { isAdmin } from '../auth.js';

const UPLOADS_DIR = path.join('/home/pi/simplifyops/people-whitelist/uploads');

const cvStorage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOADS_DIR),
  filename: (req, file, cb) => {
    const email = req.session?.user?.email || 'unknown';
    const ext = path.extname(file.originalname) || '.pdf';
    cb(null, `cv_${email.replace(/[^a-z0-9]/gi, '_')}${ext}`);
  },
});
const cvUpload = multer({
  storage: cvStorage,
  limits: { fileSize: 10 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const allowed = ['.pdf', '.doc', '.docx', '.txt'];
    cb(null, allowed.includes(path.extname(file.originalname).toLowerCase()));
  },
});

const configuredRedirectUri = (req) => {
  const proto = req.get('x-forwarded-proto') || req.protocol || 'http';
  const host = req.get('x-forwarded-host') || req.get('host');
  if (host) {
    return `${proto}://${host}/auth/callback`;
  }

  const envRedirect = (process.env.GOOGLE_REDIRECT_URI || '').trim();
  if (envRedirect) return envRedirect;

  throw new Error('Unable to determine redirect URI host');
};

const oauthClient = (req) =>
  new OAuth2Client(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    configuredRedirectUri(req)
  );

export default function authRoutes(pool) {
  const router = express.Router();

  router.get('/config', (req, res) => {
    res.json({
      redirectUri: configuredRedirectUri(req),
      host: req.get('host'),
      protocol: req.get('x-forwarded-proto') || req.protocol || 'http',
    });
  });

  router.get('/login', (req, res) => {
    const { GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET } = process.env;
    if (!GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET) {
      return res.status(503).send('Google login is not configured yet.');
    }

    const client = oauthClient(req);
    const url = client.generateAuthUrl({
      access_type: 'offline',
      scope: ['openid', 'email', 'profile'],
      prompt: 'consent',
      redirect_uri: configuredRedirectUri(req),
    });

    res.redirect(url);
  });

  router.get('/callback', async (req, res) => {
    const code = req.query.code;
    if (!code) return res.status(400).send('Missing code');

    const client = oauthClient(req);

    const { tokens } = await client.getToken({
      code,
      redirect_uri: configuredRedirectUri(req),
    });
    client.setCredentials(tokens);
    const ticket = await client.verifyIdToken({
      idToken: tokens.id_token,
      audience: process.env.GOOGLE_CLIENT_ID,
    });
    const payload = ticket.getPayload();
    const email = payload.email.toLowerCase();

    if (!(await isAdmin(pool, email))) {
      return res.status(403).send('Not an admin');
    }

    req.session.user = {
      email,
      name: payload.name,
      picture: payload.picture,
      admin: true,
    };

    req.session.save((saveErr) => {
      if (saveErr) {
        console.error('Failed to save session after login', saveErr);
        return res.status(500).send('Could not persist session');
      }
      return res.redirect('/dashboard');
    });
  });

  router.post('/logout', (req, res) => {
    req.session.destroy(() => res.json({ ok: true }));
  });

  // --- Google API authorization (expanded scopes for James) ---

  const GOOGLE_API_SCOPES = [
    'openid', 'email', 'profile',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/presentations',
  ];

  router.get('/google/connect', (req, res) => {
    const email = req.session?.user?.email;
    if (!email) return res.status(401).json({ error: 'not_signed_in' });

    const client = oauthClient(req);
    const url = client.generateAuthUrl({
      access_type: 'offline',
      scope: GOOGLE_API_SCOPES,
      prompt: 'consent',
      redirect_uri: configuredRedirectUri(req).replace('/auth/callback', '/auth/google/callback'),
      state: encodeURIComponent(email),
    });
    res.redirect(url);
  });

  router.get('/google/callback', async (req, res) => {
    const code = req.query.code;
    const email = req.session?.user?.email;
    if (!code) return res.status(400).send('Missing code');
    if (!email) return res.status(401).send('Not signed in');

    const client = oauthClient(req);
    client._redirectUri = configuredRedirectUri(req).replace('/auth/callback', '/auth/google/callback');

    const { tokens } = await client.getToken({ code, redirect_uri: client._redirectUri });

    const scopes = tokens.scope ? tokens.scope.split(' ') : [];
    await pool.query(
      `insert into google_tokens (person_email, access_token, refresh_token, token_expiry, scopes)
       values ($1, $2, $3, $4, $5)
       on conflict (person_email) do update
         set access_token = excluded.access_token,
             refresh_token = coalesce(excluded.refresh_token, google_tokens.refresh_token),
             token_expiry = excluded.token_expiry,
             scopes = excluded.scopes,
             updated_at = now()`,
      [email, tokens.access_token, tokens.refresh_token || null,
       tokens.expiry_date ? new Date(tokens.expiry_date) : null, scopes]
    );

    res.redirect('/admin/integrations');
  });

  // --- CV upload ---

  router.post('/cv', cvUpload.single('cv'), async (req, res) => {
    const email = req.session?.user?.email;
    if (!email) return res.status(401).json({ error: 'not_signed_in' });
    if (!req.file) return res.status(400).json({ error: 'no_file' });

    await pool.query(
      `update people set cv_filename = $1, cv_path = $2, cv_uploaded_at = now() where person_email = $3`,
      [req.file.originalname, req.file.filename, email]
    );
    res.json({ ok: true, filename: req.file.originalname });
  });

  router.get('/cv', async (req, res) => {
    const email = req.session?.user?.email;
    if (!email) return res.status(401).json({ error: 'not_signed_in' });
    const { rows } = await pool.query(
      'select cv_filename, cv_path, cv_uploaded_at from people where person_email = $1',
      [email]
    );
    if (!rows[0]?.cv_path) return res.json({ uploaded: false });
    res.json({ uploaded: true, filename: rows[0].cv_filename, uploaded_at: rows[0].cv_uploaded_at });
  });

  router.get('/cv/download', async (req, res) => {
    const email = req.session?.user?.email;
    if (!email) return res.status(401).json({ error: 'not_signed_in' });
    const { rows } = await pool.query(
      'select cv_filename, cv_path from people where person_email = $1', [email]
    );
    if (!rows[0]?.cv_path) return res.status(404).json({ error: 'not_found' });
    const filePath = path.join(UPLOADS_DIR, rows[0].cv_path);
    if (!fs.existsSync(filePath)) return res.status(404).json({ error: 'file_missing' });
    res.download(filePath, rows[0].cv_filename);
  });

  router.delete('/cv', async (req, res) => {
    const email = req.session?.user?.email;
    if (!email) return res.status(401).json({ error: 'not_signed_in' });
    const { rows } = await pool.query(
      'select cv_path from people where person_email = $1', [email]
    );
    if (rows[0]?.cv_path) {
      const filePath = path.join(UPLOADS_DIR, rows[0].cv_path);
      if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
      await pool.query(
        'update people set cv_filename = null, cv_path = null, cv_uploaded_at = null where person_email = $1',
        [email]
      );
    }
    res.json({ ok: true });
  });

  // --- Job preferences ---

  router.get('/job-preferences', async (req, res) => {
    const email = req.session?.user?.email;
    if (!email) return res.status(401).json({ error: 'not_signed_in' });
    const { rows } = await pool.query(
      'select * from job_preferences where person_email = $1', [email]
    );
    res.json(rows[0] || { keywords: [], min_budget: null, job_type: 'any', remote_only: true, no_agencies: true, extra_instructions: '' });
  });

  router.put('/job-preferences', async (req, res) => {
    const email = req.session?.user?.email;
    if (!email) return res.status(401).json({ error: 'not_signed_in' });
    const { keywords, min_budget, job_type, remote_only, no_agencies, extra_instructions } = req.body;
    const kw = Array.isArray(keywords) ? keywords : String(keywords || '').split(',').map(s => s.trim()).filter(Boolean);
    await pool.query(
      `insert into job_preferences (person_email, keywords, min_budget, job_type, remote_only, no_agencies, extra_instructions)
       values ($1, $2, $3, $4, $5, $6, $7)
       on conflict (person_email) do update
         set keywords = excluded.keywords,
             min_budget = excluded.min_budget,
             job_type = excluded.job_type,
             remote_only = excluded.remote_only,
             no_agencies = excluded.no_agencies,
             extra_instructions = excluded.extra_instructions,
             updated_at = now()`,
      [email, kw, min_budget || null, job_type || 'any', Boolean(remote_only), Boolean(no_agencies), extra_instructions || null]
    );
    res.json({ ok: true });
  });

  router.delete('/google/disconnect', async (req, res) => {
    const email = req.session?.user?.email;
    if (!email) return res.status(401).json({ error: 'not_signed_in' });
    await pool.query('delete from google_tokens where person_email = $1', [email]);
    res.json({ ok: true });
  });

  router.get('/google/status', async (req, res) => {
    const email = req.session?.user?.email;
    if (!email) return res.status(401).json({ error: 'not_signed_in' });
    const { rows } = await pool.query(
      'select scopes, token_expiry, updated_at from google_tokens where person_email = $1',
      [email]
    );
    if (!rows[0]) return res.json({ connected: false });
    const expired = rows[0].token_expiry && new Date(rows[0].token_expiry) < new Date();
    res.json({ connected: true, scopes: rows[0].scopes, expired, updated_at: rows[0].updated_at });
  });

  router.get('/me', async (req, res) => {
    const user = req.session?.user || null;
    if (!user?.email) {
      return res.json({ user: null });
    }

    const admin = Boolean(user.admin || (await isAdmin(pool, user.email)));
    return res.json({
      user: {
        ...user,
        admin,
      },
    });
  });

  router.get('/profile', async (req, res) => {
    const email = req.session?.user?.email;
    if (!email) return res.status(401).json({ error: 'not_signed_in' });

    const { rows } = await pool.query(
      `select person_name, person_email, telegram_id, telegram_username, telegram_first_name, telegram_last_name, telegram_last_seen_at, phone_country_code, phone_number, notes, admin, status, created_at, updated_at
       from people
       where person_email = $1
       limit 1`,
      [email.toLowerCase()]
    );

    if (!rows[0]) return res.status(404).json({ error: 'not_found' });
    res.json(rows[0]);
  });

  router.patch('/profile', async (req, res) => {
    const email = req.session?.user?.email;
    if (!email) return res.status(401).json({ error: 'not_signed_in' });

    const { person_name, telegram_id, phone_country_code, phone_number, notes } = req.body;
    const nextName = String(person_name || '').trim();
    const nextTelegramId = String(telegram_id || '').trim();
    const nextPhoneCountryCode = String(phone_country_code || '').trim();
    const nextPhoneNumber = String(phone_number || '').trim();
    const nextNotes = String(notes || '').trim();

    const { rows: beforeRows } = await pool.query('select * from people where person_email = $1 limit 1', [email.toLowerCase()]);
    const before = beforeRows[0] || null;
    if (!before) return res.status(404).json({ error: 'not_found' });

    const { rows } = await pool.query(
      `update people
       set person_name = coalesce(nullif($1, ''), person_name),
           telegram_id = nullif($2, ''),
           phone_country_code = nullif($3, ''),
           phone_number = nullif($4, ''),
           notes = nullif($5, ''),
           updated_at = now()
       where person_email = $6
       returning *`,
      [nextName, nextTelegramId, nextPhoneCountryCode, nextPhoneNumber, nextNotes, email.toLowerCase()]
    );

    const updated = rows[0] || null;
    if (!updated) return res.status(404).json({ error: 'not_found' });

    req.session.user = {
      ...req.session.user,
      name: updated.person_name,
    };

    await logAudit(pool, {
      actorEmail: email,
      action: 'update_profile',
      subjectEmail: email,
      oldValue: before,
      newValue: updated,
    });

    res.json(updated);
  });

  return router;
}
