import express from 'express';
import { requireAdmin } from '../middleware/requireAdmin.js';

export default function adminRoutes(pool) {
  const router = express.Router();
  const adminOnly = requireAdmin(pool);

  router.get('/dashboard', adminOnly, async (_req, res) => {
    const [{ rows: people }, { rows: audit }] = await Promise.all([
      pool.query('select person_name, person_email, telegram_id, phone_country_code, phone_number, admin, status, notes, created_at, updated_at from people order by created_at desc'),
      pool.query('select actor_email, action, subject_email, created_at from audit_log order by created_at desc limit 25'),
    ]);

    res.json({ people, audit });
  });

  return router;
}
