import express from 'express';
import { requireAdmin } from '../middleware/requireAdmin.js';

export default function activityRoutes(pool) {
  const router = express.Router();
  const adminOnly = requireAdmin(pool);

  // GET /api/activity?status=all|completed|processing|failed_retryable|failed_needs_review
  router.get('/', adminOnly, async (req, res) => {
    const status = req.query.status || 'all';
    const limit = Math.min(parseInt(req.query.limit) || 100, 500);
    const where = status === 'all' ? '' : 'WHERE w.status = $2';
    const params = status === 'all' ? [limit] : [limit, status];

    const { rows } = await pool.query(`
      SELECT
        w.id, w.request_id, w.status, w.attempt_count, w.error_summary,
        left(w.reply_text, 120)   AS reply_preview,
        w.created_at, w.updated_at,
        r.channel, r.from_id, r.from_name, r.chat_id,
        left(r.message_text, 200) AS message_preview,
        length(r.message_text)    AS message_length
      FROM work_items w
      JOIN requests r ON r.id = w.request_id
      ${where}
      ORDER BY w.created_at DESC
      LIMIT $1
    `, params);

    res.json(rows);
  });

  // GET /api/activity/:id — full detail for one work item
  router.get('/:id', adminOnly, async (req, res) => {
    const { rows } = await pool.query(`
      SELECT
        w.*,
        r.channel, r.from_id, r.from_name, r.chat_id,
        r.message_text,
        r.created_at AS requested_at
      FROM work_items w
      JOIN requests r ON r.id = w.request_id
      WHERE w.id = $1
    `, [req.params.id]);

    if (!rows[0]) return res.status(404).json({ error: 'not_found' });
    res.json(rows[0]);
  });

  return router;
}
