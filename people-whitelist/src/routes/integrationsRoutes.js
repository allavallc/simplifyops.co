import express from 'express';
import fs from 'node:fs';
import yaml from 'js-yaml';

const HERMES_CONFIG = '/home/pi/.hermes/profiles/simplifyops/config.yaml';

const GOOGLE_SERVICES = {
  'google-gmail':     { label: 'Gmail',    icon: '✉️',  scope: 'https://www.googleapis.com/auth/gmail.modify' },
  'google-calendar':  { label: 'Calendar', icon: '📅',  scope: 'https://www.googleapis.com/auth/calendar' },
  'google-drive':     { label: 'Drive',    icon: '📁',  scope: 'https://www.googleapis.com/auth/drive' },
  'google-sheets':    { label: 'Sheets',   icon: '📊',  scope: 'https://www.googleapis.com/auth/spreadsheets' },
  'google-docs':      { label: 'Docs',     icon: '📄',  scope: 'https://www.googleapis.com/auth/documents' },
  'google-slides':    { label: 'Slides',   icon: '📽️',  scope: 'https://www.googleapis.com/auth/presentations' },
  'google-meet':      { label: 'Meet',     icon: '📹',  scope: null },
};

function readHermesConfig() {
  return yaml.load(fs.readFileSync(HERMES_CONFIG, 'utf8'));
}

function writeHermesConfig(config) {
  fs.writeFileSync(HERMES_CONFIG + '.tmp', yaml.dump(config, { lineWidth: 120 }));
  fs.renameSync(HERMES_CONFIG + '.tmp', HERMES_CONFIG);
}

export default function integrationsRoutes(pool) {
  const router = express.Router();

  const requireAdmin = async (req, res, next) => {
    const email = req.session?.user?.email;
    if (!email || !req.session?.user?.admin) return res.status(401).json({ error: 'not_admin' });
    next();
  };

  // GET /api/integrations — list all Google services with their enabled state + auth status
  router.get('/', requireAdmin, async (req, res) => {
    const email = req.session.user.email;
    const config = readHermesConfig();
    const mcpServers = config.mcp_servers || {};

    const { rows: tokenRows } = await pool.query(
      'select scopes, token_expiry, updated_at from google_tokens where person_email = $1',
      [email]
    );
    const token = tokenRows[0] || null;
    const authorized = Boolean(token);
    const authorizedScopes = token?.scopes || [];
    const tokenExpired = token?.token_expiry && new Date(token.token_expiry) < new Date();

    const services = Object.entries(GOOGLE_SERVICES).map(([key, meta]) => {
      const entry = mcpServers[key] || {};
      const enabled = entry.enabled !== false && entry.enabled !== 'false';
      const scopeAuthorized = meta.scope ? authorizedScopes.includes(meta.scope) : false;
      return {
        id: key,
        label: meta.label,
        icon: meta.icon,
        enabled,
        scope: meta.scope,
        scope_authorized: scopeAuthorized,
      };
    });

    res.json({
      services,
      auth: { connected: authorized, expired: tokenExpired, updated_at: token?.updated_at },
    });
  });

  // POST /api/integrations/:service/toggle — enable or disable a service
  router.post('/:service/toggle', requireAdmin, (req, res) => {
    const { service } = req.params;
    if (!GOOGLE_SERVICES[service]) return res.status(404).json({ error: 'unknown_service' });

    const config = readHermesConfig();
    if (!config.mcp_servers?.[service]) return res.status(404).json({ error: 'service_not_in_config' });

    const current = config.mcp_servers[service].enabled;
    const currentBool = current !== false && current !== 'false';
    config.mcp_servers[service].enabled = !currentBool;
    writeHermesConfig(config);

    res.json({ id: service, enabled: !currentBool });
  });

  return router;
}
