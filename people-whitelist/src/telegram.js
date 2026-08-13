const telegramSourceFromUpdate = (update) =>
  update?.message?.from ||
  update?.edited_message?.from ||
  update?.channel_post?.from ||
  update?.callback_query?.from ||
  update?.inline_query?.from ||
  update?.chosen_inline_result?.from ||
  null;

const telegramChatIdFromUpdate = (update) =>
  update?.message?.chat?.id ||
  update?.edited_message?.chat?.id ||
  update?.channel_post?.chat?.id ||
  update?.callback_query?.message?.chat?.id ||
  null;

const telegramTextFromUpdate = (update) =>
  update?.message?.text ||
  update?.edited_message?.text ||
  update?.channel_post?.text ||
  update?.callback_query?.data ||
  null;

export const telegramIdentityFromUpdate = (update) => {
  const source = telegramSourceFromUpdate(update);
  if (!source?.id) return null;

  return {
    telegram_id: String(source.id),
    telegram_username: source.username || null,
    telegram_first_name: source.first_name || null,
    telegram_last_name: source.last_name || null,
  };
};

const telegramDisplayName = (person) => {
  const profileName = [person?.telegram_first_name, person?.telegram_last_name].filter(Boolean).join(' ').trim();
  return profileName || person?.person_name || person?.person_email || 'there';
};

const telegramApiUrl = (token, method) => `https://api.telegram.org/bot${token}/${method}`;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function sendTelegramMessage(token, chatId, text) {
  if (!token || chatId == null || !text) return null;

  const response = await fetch(telegramApiUrl(token, 'sendMessage'), {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      disable_web_page_preview: true,
    }),
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok || payload?.ok === false) {
    const details = payload ? JSON.stringify(payload) : `${response.status} ${response.statusText}`;
    throw new Error(`telegram sendMessage failed: ${details}`);
  }

  return payload;
}

export async function handleTelegramUpdate(pool, update, options = {}) {
  const identity = telegramIdentityFromUpdate(update);
  if (!identity) {
    return { ok: true, matched: false, reason: 'no_sender' };
  }

  const { rows } = await pool.query(
    `select person_name, person_email, telegram_id, telegram_username, telegram_first_name, telegram_last_name, telegram_last_seen_at, admin, status
     from people
     where telegram_id = $1
     limit 1`,
    [identity.telegram_id]
  );

  const existing = rows[0] || null;
  if (!existing) {
    const unmatched = {
      ok: true,
      matched: false,
      telegram_id: identity.telegram_id,
      reply_text: 'I do not have this Telegram account linked yet.',
    };

    if (options.respond && options.sendReply === true) {
      const token = (process.env.TELEGRAM_BOT_TOKEN || '').trim();
      const chatId = telegramChatIdFromUpdate(update);
      if (token && chatId != null) {
        await sendTelegramMessage(token, chatId, unmatched.reply_text);
      }
    }

    return unmatched;
  }

  const firstRecognition = !existing.telegram_last_seen_at;

  const { rows: updatedRows } = await pool.query(
    `update people
     set telegram_username = coalesce($2, telegram_username),
         telegram_first_name = coalesce($3, telegram_first_name),
         telegram_last_name = coalesce($4, telegram_last_name),
         telegram_last_seen_at = now(),
         updated_at = now()
     where telegram_id = $1
     returning person_name, person_email, telegram_id, telegram_username, telegram_first_name, telegram_last_name, telegram_last_seen_at, admin, status`,
    [
      identity.telegram_id,
      identity.telegram_username,
      identity.telegram_first_name,
      identity.telegram_last_name,
    ]
  );

  const person = updatedRows[0] || existing;
  const reply_text = `Recognized as ${telegramDisplayName(person)}.`;
  const result = {
    ok: true,
    matched: true,
    person,
    reply_text,
  };

  if (options.respond && options.sendReply === true && firstRecognition) {
    const token = (process.env.TELEGRAM_BOT_TOKEN || '').trim();
    const chatId = telegramChatIdFromUpdate(update);
    if (token && chatId != null && telegramTextFromUpdate(update)) {
      await sendTelegramMessage(token, chatId, reply_text);
    }
  }

  return result;
}

export function startTelegramPoller(pool) {
  const token = (process.env.TELEGRAM_BOT_TOKEN || '').trim();
  const enabled = (process.env.TELEGRAM_ENABLE_POLLING || 'true').trim().toLowerCase() !== 'false';

  if (!token || !enabled) {
    return { started: false, reason: token ? 'polling_disabled' : 'missing_token' };
  }

  let stopped = false;
  let offset = 0;

  const loop = async () => {
    while (!stopped) {
      try {
        const url = new URL(telegramApiUrl(token, 'getUpdates'));
        url.searchParams.set('timeout', '30');
        url.searchParams.set('limit', '100');
        if (offset > 0) {
          url.searchParams.set('offset', String(offset));
        }

        const response = await fetch(url, { method: 'GET' });
        const payload = await response.json().catch(() => null);
        if (!response.ok || payload?.ok === false) {
          const details = payload ? JSON.stringify(payload) : `${response.status} ${response.statusText}`;
          throw new Error(`telegram getUpdates failed: ${details}`);
        }

        const updates = Array.isArray(payload?.result) ? payload.result : [];
        for (const update of updates) {
          if (typeof update?.update_id === 'number') {
            offset = Math.max(offset, update.update_id + 1);
          }

          try {
            await handleTelegramUpdate(pool, update, { respond: true });
          } catch (updateErr) {
            console.error('Failed to handle Telegram update', updateErr);
          }
        }
      } catch (err) {
        console.error('Telegram poller error', err);
        await sleep(5000);
      }
    }
  };

  loop().catch((err) => {
    console.error('Telegram poller crashed', err);
  });

  return {
    started: true,
    mode: 'polling',
    stop() {
      stopped = true;
    },
  };
}
