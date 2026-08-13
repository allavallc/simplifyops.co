import express from 'express';
import { logAudit } from '../audit.js';
import { requireAdmin } from '../middleware/requireAdmin.js';

const parseBool = (value) => {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number') return value !== 0;
  if (typeof value === 'string') return ['true', '1', 'yes', 'on'].includes(value.trim().toLowerCase());
  return false;
};

async function countAdmins(pool) {
  const { rows } = await pool.query('select count(*)::int as count from people where admin = true');
  return rows[0]?.count || 0;
}

export default function peopleRoutes(pool) {
  const router = express.Router();
  const adminOnly = requireAdmin(pool);

  router.get('/', adminOnly, async (_req, res) => {
    const { rows } = await pool.query('select * from people order by created_at desc');
    res.json(rows);
  });

  router.get('/:email', adminOnly, async (req, res) => {
    const email = String(req.params.email || '').toLowerCase();
    const { rows } = await pool.query('select * from people where person_email = $1 limit 1', [email]);
    if (!rows[0]) return res.status(404).json({ error: 'not_found' });
    res.json(rows[0]);
  });

  router.post('/', adminOnly, async (req, res) => {
    const { person_name, person_email, telegram_id, phone_country_code, phone_number, notes, status, admin, authority, can_converse, can_influence } = req.body;
    const email = String(person_email || '').toLowerCase().trim();
    const name = String(person_name || '').trim() || null;
    const telegramId = String(telegram_id || '').trim() || null;
    const phoneCountryCode = String(phone_country_code || '').trim() || null;
    const phoneNumber = String(phone_number || '').trim() || null;
    const isAdmin = parseBool(admin);
    const nextStatus = String(status || 'allowed').trim() || 'allowed';
    const nextAuthority = String(authority || 'member').trim() || 'member';
    const nextCanConverse = can_converse === undefined ? true : parseBool(can_converse);
    const nextCanInfluence = can_influence === undefined ? true : parseBool(can_influence);

    const result = await pool.query(
      `insert into people (person_name, person_email, telegram_id, phone_country_code, phone_number, admin, authority, can_converse, can_influence, status, notes, created_by, updated_at)
       values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, now())
       on conflict (person_email) do update
       set person_name = excluded.person_name,
           telegram_id = excluded.telegram_id,
           phone_country_code = excluded.phone_country_code,
           phone_number = excluded.phone_number,
           admin = excluded.admin,
           authority = excluded.authority,
           can_converse = excluded.can_converse,
           can_influence = excluded.can_influence,
           status = excluded.status,
           notes = excluded.notes,
           created_by = excluded.created_by,
           updated_at = now()
       returning *`,
      [name, email, telegramId, phoneCountryCode, phoneNumber, isAdmin, nextAuthority, nextCanConverse, nextCanInfluence, nextStatus, notes || null, req.session.user.email]
    );

    await logAudit(pool, {
      actorEmail: req.session.user.email,
      action: 'upsert_person',
      subjectEmail: email,
      newValue: result.rows[0],
    });

    res.json(result.rows[0]);
  });

  router.patch('/:email', adminOnly, async (req, res) => {
    const email = String(req.params.email || '').toLowerCase();
    const { status, notes, person_name, person_email, telegram_id, phone_country_code, phone_number, admin, authority, can_converse, can_influence } = req.body;
    const nextEmail = String(person_email || email).toLowerCase().trim();
    const nextTelegramId = telegram_id === undefined ? null : String(telegram_id || '').trim() || null;
    const nextPhoneCountryCode = phone_country_code === undefined ? null : String(phone_country_code || '').trim() || null;
    const nextPhoneNumber = phone_number === undefined ? null : String(phone_number || '').trim() || null;
    const nextAdmin = admin === undefined ? null : parseBool(admin);
    const nextAuthority = authority === undefined ? null : String(authority || 'member').trim();
    const nextCanConverse = can_converse === undefined ? null : parseBool(can_converse);
    const nextCanInfluence = can_influence === undefined ? null : parseBool(can_influence);
    const { rows: beforeRows } = await pool.query('select * from people where person_email = $1', [email]);
    const before = beforeRows[0] || null;

    if (before?.admin && nextAdmin === false && (await countAdmins(pool)) <= 1) {
      return res.status(400).json({ error: 'cannot_remove_last_admin' });
    }

    const result = await pool.query(
      `update people
       set person_email = $1,
           telegram_id = coalesce($2, telegram_id),
           phone_country_code = coalesce($3, phone_country_code),
           phone_number = coalesce($4, phone_number),
           admin = coalesce($5, admin),
           authority = coalesce($6, authority),
           can_converse = coalesce($7, can_converse),
           can_influence = coalesce($8, can_influence),
           status = coalesce($9, status),
           notes = coalesce($10, notes),
           person_name = coalesce($11, person_name),
           updated_at = now()
       where person_email = $12
       returning *`,
      [nextEmail, nextTelegramId, nextPhoneCountryCode, nextPhoneNumber, nextAdmin, nextAuthority, nextCanConverse, nextCanInfluence, status || null, notes || null, person_name || null, email]
    );

    await logAudit(pool, {
      actorEmail: req.session.user.email,
      action: 'update_person',
      subjectEmail: email,
      oldValue: before,
      newValue: result.rows[0],
    });

    res.json(result.rows[0]);
  });

  router.delete('/:email', adminOnly, async (req, res) => {
    const email = String(req.params.email || '').toLowerCase();
    const { rows: beforeRows } = await pool.query('select * from people where person_email = $1', [email]);
    const before = beforeRows[0] || null;

    if (before?.admin && (await countAdmins(pool)) <= 1) {
      return res.status(400).json({ error: 'cannot_delete_last_admin' });
    }

    await pool.query('delete from people where person_email = $1', [email]);

    await logAudit(pool, {
      actorEmail: req.session.user.email,
      action: 'delete_person',
      subjectEmail: email,
      oldValue: before,
    });

    res.json({ ok: true });
  });

  return router;
}
