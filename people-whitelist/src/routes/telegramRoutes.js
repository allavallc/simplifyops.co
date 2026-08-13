import express from 'express';
import { handleTelegramUpdate } from '../telegram.js';

export default function telegramRoutes(pool) {
  const router = express.Router();

  router.get('/status', (_req, res) => {
    res.json({
      ok: true,
      configured: Boolean((process.env.TELEGRAM_BOT_TOKEN || '').trim()),
      polling: (process.env.TELEGRAM_ENABLE_POLLING || 'true').trim().toLowerCase() !== 'false',
    });
  });

  router.post('/webhook', async (req, res) => {
    const expectedSecret = (process.env.TELEGRAM_WEBHOOK_SECRET || '').trim();
    if (expectedSecret) {
      const receivedSecret = String(req.get('x-telegram-bot-api-secret-token') || '').trim();
      if (receivedSecret !== expectedSecret) {
        return res.status(403).json({ error: 'bad_secret' });
      }
    }

    const result = await handleTelegramUpdate(pool, req.body || {}, { respond: false });
    return res.json(result);
  });

  router.get('/lookup/:telegramId', async (req, res) => {
    const telegramId = String(req.params.telegramId || '').trim();
    if (!telegramId) return res.status(400).json({ error: 'missing_telegram_id' });

    const { rows } = await pool.query(
      `select person_name, person_email, telegram_id, telegram_username, telegram_first_name, telegram_last_name, telegram_last_seen_at, admin, status
       from people
       where telegram_id = $1
       limit 1`,
      [telegramId]
    );

    if (!rows[0]) return res.status(404).json({ matched: false });
    return res.json({ matched: true, person: rows[0] });
  });

  return router;
}
