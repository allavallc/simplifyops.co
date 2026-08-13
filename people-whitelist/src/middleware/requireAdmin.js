import { isAdmin } from '../auth.js';

export function requireAdmin(pool) {
  return async (req, res, next) => {
    const email = req.session?.user?.email;
    if (!email) return res.status(401).json({ error: 'not_signed_in' });
    if (!(await isAdmin(pool, email))) return res.status(403).json({ error: 'not_admin' });
    next();
  };
}
