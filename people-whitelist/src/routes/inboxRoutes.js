import express from 'express';
import { randomUUID } from 'node:crypto';

const GATEWAY_INTERNAL_URL = process.env.GATEWAY_INTERNAL_URL || 'http://127.0.0.1:3001';

export default function inboxRoutes(pool) {
  const router = express.Router();

  const requireAdmin = (req, res, next) => {
    if (!req.session?.user?.admin) return res.status(401).json({ error: 'not_admin' });
    next();
  };

  // POST /api/inbox — called by gateway to queue an unknown sender
  router.post('/', async (req, res) => {
    const { request_id, channel, from_id, from_name, chat_id, message_text, raw } = req.body;
    const normalizedRequestId = String(request_id || '').trim() || randomUUID();
    if (!channel || !from_id || !chat_id || !message_text) {
      return res.status(400).json({ error: 'missing_fields' });
    }
    // Deduplicate by request_id first so retries stay idempotent.
    const existing = await pool.query(
      `select id from contact_requests where request_id = $1 limit 1`,
      [normalizedRequestId]
    );
    if (existing.rows[0]) {
      await pool.query(
        `update contact_requests set channel = $1, from_id = $2, from_name = $3, chat_id = $4, message_text = $5, raw = $6, updated_at = now() where id = $7`,
        [channel, String(from_id), from_name || null, String(chat_id), message_text, raw ? JSON.stringify(raw) : null, existing.rows[0].id]
      );
      return res.json({ queued: true, id: existing.rows[0].id, request_id: normalizedRequestId, deduplicated: true });
    }
    const { rows } = await pool.query(
      `insert into contact_requests (request_id, channel, from_id, from_name, chat_id, message_text, raw)
       values ($1, $2, $3, $4, $5, $6, $7) returning id, request_id`,
      [normalizedRequestId, channel, String(from_id), from_name || null, String(chat_id), message_text, raw ? JSON.stringify(raw) : null]
    );
    res.json({ queued: true, id: rows[0].id, request_id: rows[0].request_id });
  });

  // GET /api/inbox — list requests
  router.get('/', requireAdmin, async (req, res) => {
    const status = req.query.status || 'pending';
    const where = status === 'all' ? '' : `where status = $1`;
    const params = status === 'all' ? [] : [status];
    const { rows } = await pool.query(
      `select id, request_id, channel, from_id, from_name, chat_id,
              left(message_text, 300) as message_preview,
              length(message_text) as message_length,
              status, created_at, reviewed_at, reviewed_by
       from contact_requests
       ${where}
       order by created_at desc`,
      params
    );
    res.json(rows);
  });

  // POST /api/inbox/:id/approve
  router.post('/:id/approve', requireAdmin, async (req, res) => {
    const { id } = req.params;
    const reviewerEmail = req.session.user.email;

    const { rows } = await pool.query(
      `update contact_requests set status = 'approved', reviewed_at = now(), reviewed_by = $1, updated_at = now()
       where id = $2 and status in ('pending','ignored') returning *`,
      [reviewerEmail, id]
    );
    if (!rows[0]) return res.status(404).json({ error: 'not_found' });

    const req_row = rows[0];

    // Add to people DB with governance flags
    await pool.query(
      `insert into people (person_name, person_email, telegram_id, telegram_first_name, status, authority, can_converse, can_influence, created_by)
       values ($1, $2, $3, $4, 'allowed', 'contact', true, false, $5)
       on conflict (person_email) do update
         set status = 'allowed',
             authority = coalesce(people.authority, 'contact'),
             can_converse = true,
             telegram_id = coalesce(excluded.telegram_id, people.telegram_id),
             updated_at = now()`,
      [req_row.from_name || null, `${req_row.from_id}@telegram`, req_row.from_id, req_row.from_name || null, reviewerEmail]
    );

    // Trigger gateway to send the reply
    const createdAt = new Date(req_row.created_at).toISOString();
    try {
      const response = await fetch(`${GATEWAY_INTERNAL_URL}/internal/reply`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          request_id: req_row.request_id,
          channel: req_row.channel,
          from_id: req_row.from_id,
          chat_id: req_row.chat_id,
          text: req_row.message_text,
          requested_at: createdAt,
        }),
      });
      if (!response.ok) {
        console.error('Gateway reply trigger failed:', response.status);
      }
    } catch (err) {
      console.error('Could not reach gateway for reply:', err.message);
    }

    res.json({ ok: true, request: req_row });
  });

  // POST /api/inbox/:id/reject
  router.post('/:id/reject', requireAdmin, async (req, res) => {
    const { rows } = await pool.query(
      `update contact_requests set status = 'rejected', reviewed_at = now(), reviewed_by = $1, updated_at = now()
       where id = $2 returning id`,
      [req.session.user.email, req.params.id]
    );
    if (!rows[0]) return res.status(404).json({ error: 'not_found' });
    res.json({ ok: true });
  });

  // POST /api/inbox/:id/ignore
  router.post('/:id/ignore', requireAdmin, async (req, res) => {
    const { rows } = await pool.query(
      `update contact_requests set status = 'ignored', reviewed_at = now(), reviewed_by = $1, updated_at = now()
       where id = $2 returning id`,
      [req.session.user.email, req.params.id]
    );
    if (!rows[0]) return res.status(404).json({ error: 'not_found' });
    res.json({ ok: true });
  });

  // GET /api/inbox/count — pending count for badge
  router.get('/count', requireAdmin, async (req, res) => {
    const { rows } = await pool.query(
      `select count(*)::int as count from contact_requests where status = 'pending'`
    );
    res.json({ pending: rows[0].count });
  });

  return router;
}
