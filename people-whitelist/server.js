import dotenv from 'dotenv';
dotenv.config();

import express from 'express';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import session from 'express-session';
import pg from 'pg';
import connectPgSimple from 'connect-pg-simple';
import { initDb } from './src/db.js';
import { bootstrapAdmin } from './src/auth.js';
import { isAdmin } from './src/auth.js';
import authRoutes from './src/routes/authRoutes.js';
import peopleRoutes from './src/routes/peopleRoutes.js';
import adminRoutes from './src/routes/adminRoutes.js';
import telegramRoutes from './src/routes/telegramRoutes.js';
import integrationsRoutes from './src/routes/integrationsRoutes.js';
import inboxRoutes from './src/routes/inboxRoutes.js';
import activityRoutes from './src/routes/activityRoutes.js';
import { startTelegramPoller } from './src/telegram.js';

const { Pool } = pg;
const PgSession = connectPgSimple(session);

const app = express();
const port = process.env.PORT || 3000;
app.set('trust proxy', 1);
const host = process.env.HOST || '0.0.0.0';
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const publicDir = path.join(__dirname, 'public');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

await initDb(pool);
await bootstrapAdmin(pool);
startTelegramPoller(pool);

app.use(express.json());
app.use(express.urlencoded({ extended: false }));
app.use(
  session({
    store: new PgSession({
      pool,
      tableName: 'sessions',
    }),
    secret: process.env.SESSION_SECRET || 'dev-only-secret',
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      sameSite: 'lax',
      secure: 'auto',
    },
  })
);

app.use(express.static('public', { index: false }));
app.use('/auth', authRoutes(pool));
app.use('/api/people', peopleRoutes(pool));
app.use('/api/admin', adminRoutes(pool));
app.use('/api/telegram', telegramRoutes(pool));
app.use('/api/integrations', integrationsRoutes(pool));
app.use('/api/inbox', inboxRoutes(pool));
app.use('/api/activity', activityRoutes(pool));

const sendPage = (file) => (_req, res) => res.sendFile(path.join(publicDir, file));
const signedInOnly = (req, res, next) => {
  const email = req.session?.user?.email;
  if (!email) return res.redirect('/');
  return next();
};
const adminPageOnly = (pool) => async (req, res, next) => {
  const email = req.session?.user?.email;
  if (!email) return res.status(401).send('Not signed in');
  if (!(await isAdmin(pool, email))) return res.status(403).send('Not an admin');
  return next();
};

app.get('/', sendPage('login.html'));
app.get('/login', sendPage('login.html'));
app.get('/logout', sendPage('logout.html'));
app.get('/dashboard', signedInOnly, sendPage('dashboard.html'));
app.get('/profile', signedInOnly, sendPage('profile.html'));
app.get('/admin', adminPageOnly(pool), sendPage('admin.html'));
app.get('/admin/integrations', adminPageOnly(pool), sendPage('integrations.html'));
app.get('/admin/inbox', adminPageOnly(pool), sendPage('inbox.html'));
app.get('/admin/activity', adminPageOnly(pool), sendPage('activity.html'));
app.get('/admin/activity/:id', adminPageOnly(pool), sendPage('activity-detail.html'));
app.get('/people', sendPage('people-index.html'));
app.get('/people/new', sendPage('person-form.html'));
app.get('/people/:email/edit', sendPage('person-form.html'));
app.get('/people/:email', sendPage('person-view.html'));

app.get('/dashboard.html', (_req, res) => res.redirect('/dashboard'));
app.get('/profile.html', (_req, res) => res.redirect('/profile'));
app.get('/admin.html', (_req, res) => res.redirect('/admin'));

app.get('/health', (_req, res) => {
  res.json({ ok: true });
});

app.listen(port, host, () => {
  console.log(`People whitelist app listening on ${host}:${port}`);
});
