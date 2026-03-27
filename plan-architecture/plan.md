# Project: SimplifyOps Automated SEO Blog Engine

## Objective
Build an automated weekly blog system using Hermes Agent that:
- Generates SEO-optimized blog posts weekly
- References private knowledge from `00_coo_brain` repo
- Requires Telegram approval before publishing
- Publishes to GitHub Pages (simplifyops.co)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  Hermes Agent (VPS/Local Machine)               │
│  ├─ Cron Scheduler (Monday 9am)                 │
│  ├─ Ollama (Llama 3.1 8B initially)             │
│  ├─ Web Search Tool                             │
│  └─ Telegram Gateway (approval workflow)        │
└──────────┬──────────────────────────────────────┘
           │
           ├─► Read: ~/.hermes/brain/ (cloned 00_coo_brain)
           ├─► Search: Web trends in business ops
           ├─► Generate: Blog post draft
           ├─► Send: Draft to Telegram for approval
           ├─► Receive: "approve" or "revise: feedback"
           └─► Publish: Commit to simplifyops-site repo
                        │
                        ▼
           ┌────────────────────────────┐
           │ GitHub Pages                │
           │ simplifyops.co              │
           │ Auto-deploys on git push    │
           └────────────────────────────┘
```

---

## Components

### 1. Hermes Installation & Setup
```bash
# Install Hermes
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc

# Run setup wizard
hermes setup
```

### 2. Configuration Files

**`~/.hermes/.env`**
```bash
# GitHub access
GITHUB_TOKEN=ghp_your_personal_access_token

# Telegram bot
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_HOME_CHANNEL=your_chat_id

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
```

**`~/.hermes/config.yaml`**
```yaml
# Model configuration
model_provider: ollama
model_name: hermes-3

# Terminal backend
terminal:
  backend: local
  cwd: "~"

# Telegram gateway
telegram:
  enabled: true
  require_approval_for_publish: true

# Cron settings
cron:
  enabled: true
```

### 3. Knowledge Base Setup

**Clone private brain repo:**
```bash
cd ~/.hermes/
git clone https://github.com/allavallc/00_coo_brain.git brain

# Keep it updated (optional cron)
(crontab -l 2>/dev/null; echo "0 */6 * * * cd ~/.hermes/brain && git pull") | crontab -
```

**Expected structure in `00_coo_brain`:**
```
00_coo_brain/
├── README.md
├── experience/
│   ├── project-summaries.md
│   ├── client-wins.md
│   └── methodologies.md
├── expertise/
│   ├── operations.md
│   ├── automation.md
│   └── cost-optimization.md
└── case-studies/
    └── *.md
```

### 4. GitHub Pages Repo Setup

**Repository:** `allavallc/simplifyops-site`

**Structure:**
```
simplifyops-site/
├── index.html           # Landing page
├── _config.yml          # Jekyll config (optional)
├── blog/
│   ├── index.html       # Blog listing
│   └── posts/           # Individual posts
│       └── YYYY-MM-DD-title.md
└── assets/
    └── css/
```

**Enable GitHub Pages:**
- Settings > Pages > Source: `main` branch

### 5. Hermes Skill for Blog Generation

**Create custom skill: `~/.hermes/skills/blog-writer.md`**

```markdown
---
name: blog-writer
description: Generates SEO blog posts combining web trends with private knowledge
triggers:
  - write blog
  - generate blog post
  - create content
---

# Blog Writer Skill

## Workflow

1. **Research Trends**
   - Use `web_search` for "business operations trends 2026"
   - Use `web_search` for "small business automation trends"
   - Extract top 3-5 trending topics

2. **Mine Knowledge Base**
   - Search `~/.hermes/brain/` for relevant experience
   - Use `terminal` with grep/ripgrep to find matching content
   - Extract specific examples, metrics, methodologies

3. **Generate Post**
   - Title: SEO-friendly, includes main keyword
   - Length: 1000-1500 words
   - Structure:
     * Hook (trending problem)
     * Your experience addressing it
     * Step-by-step approach
     * Results/metrics
     * Call-to-action (contact for services)
   - SEO: Include meta description, keywords naturally

4. **Format for Jekyll**
```yaml
---
layout: post
title: "Your SEO Title Here"
date: YYYY-MM-DD
categories: [business-ops, automation]
description: "Meta description for SEO"
---

[Post content in markdown]
```

5. **Save Draft**
   - Write to `/tmp/blog-draft-YYYY-MM-DD.md`
   - Do NOT publish yet

6. **Request Approval**
   - Use `send_message` to Telegram
   - Include: topic, word count, key points
   - Attach draft file
   - Wait for "approve" or "revise: [feedback]"

7. **Publish (after approval)**
```bash
cd ~/simplifyops-site
cp /tmp/blog-draft-*.md blog/posts/$(date +%Y-%m-%d)-post.md
git add blog/posts/
git commit -m "New blog post: [TITLE]"
git push origin main
```

## Tools Required
- web_search
- terminal
- read_file
- write_file
- send_message (Telegram)
```

### 6. Cron Job Configuration

```bash
# Start Hermes gateway (enables Telegram)
hermes gateway start

# Create weekly blog job
hermes cron create "0 9 * * MON" \
  "Use the blog-writer skill to create this week's blog post. \
   Research current business operations trends, \
   reference my experience from ~/.hermes/brain/, \
   write SEO-optimized post, \
   send draft to Telegram for my approval, \
   then publish to simplifyops-site repo after I approve." \
  --skill blog-writer \
  --delivery telegram
```

---

## Approval Workflow

**When cron runs:**
1. Hermes sends Telegram message:
   ```
   📝 Weekly Blog Draft Ready
   
   Topic: "5 Ways AI Reduces Business Ops Costs in 2026"
   Word count: 1,247
   Keywords: business automation, cost reduction, AI ops
   
   Key points:
   - References your Kubernetes cost optimization project
   - Includes 40% cost reduction metric
   - Links to simplifyOps.co services
   
   Draft: [attached file]
   
   Reply "approve" to publish or "revise: your feedback"
   ```

2. **You reply:**
   - `approve` → Hermes commits and pushes to GitHub
   - `revise: make intro more personal` → Hermes rewrites and re-sends
   - `cancel` → Skips this week

---

## Implementation Checklist

- [ ] Install Hermes Agent
- [ ] Configure Ollama with Hermes-3 model
- [ ] Set up Telegram bot and get credentials
- [ ] Create GitHub Personal Access Token (repo scope)
- [ ] Clone `00_coo_brain` to `~/.hermes/brain/`
- [ ] Create `simplifyops-site` repo with GitHub Pages enabled
- [ ] Add all credentials to `~/.hermes/.env`
- [ ] Create `blog-writer` skill
- [ ] Install and configure Hermes gateway
- [ ] Create weekly cron job
- [ ] Test approval workflow
- [ ] Verify first publish to GitHub Pages

---

## Testing Before Production

```bash
# Test the workflow manually
hermes chat --skill blog-writer

# In chat, say:
"Generate a blog post about current DevOps trends"

# Verify it:
# - Searches web
# - Reads brain repo
# - Generates quality content
# - Sends to Telegram
# - Waits for approval
# - Publishes correctly
```

---

## Future Enhancements

1. **Upgrade model:** Switch from Ollama to Claude Sonnet
   ```bash
   hermes model
   # Select: openrouter:anthropic/claude-sonnet-4
   ```

2. **Add social promotion:**
   - Auto-post to LinkedIn/Twitter after publish
   - Generate social media snippets

3. **SEO tracking:**
   - Monitor Google Search Console
   - Adjust topics based on performance

4. **Multi-post cadence:**
   - Change from weekly to 2x/week or daily

---

## Cost Analysis

**Initial (Ollama local):**
- Hosting: $0 (GitHub Pages free)
- Model: $0 (Ollama free)
- Total: $0/month

**Upgraded (Claude Sonnet):**
- Hosting: $0
- Model: ~$0.15/post × 4/month = $0.60/month
- Total: $0.60/month

**VPS if running Hermes 24/7:**
- DigitalOcean: $5/month
- Total with Claude: $5.60/month

---

## Security Considerations

- `00_coo_brain` stays private (only cloned locally)
- GitHub token has minimal scope (repo only)
- Telegram approval prevents auto-publishing mistakes
- Hermes runs in isolated environment
- No credit cards or sensitive data in prompts

---

**Ready for Claude Code implementation.**
