import { isWhitelisted } from '../whitelist.js';

export function requireWhitelist(pool) {
  return async (req, res, next) => {
    const email = req.body?.person_email || req.query?.person_email || req.session?.user?.email;
    if (!email) return res.status(400).json({ error: 'missing_email' });
    if (!(await isWhitelisted(pool, email))) return res.status(403).json({ error: 'not_whitelisted' });
    next();
  };
}
