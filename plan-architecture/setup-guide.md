# SimplifyOps Hermes Setup Guide

## Overview

This guide sets up automated weekly blog generation on your Windows laptop. If your laptop is asleep when the scheduled time hits, the task runs when you next wake it.

```
Weekly Schedule (Monday 9am)
    │
    └─► Laptop awake?
            ├─ Yes → Hermes runs immediately
            └─ No  → Runs when you next open laptop
                         │
                         ▼
                    Hermes generates blog draft
                         │
                         ▼
                    Sends to Telegram for approval
                         │
                         ▼
                    You approve → Publishes to GitHub Pages
```

---

## Phase 1: Install Core Tools

### 1.1 Install Ollama

1. Download from: https://ollama.com/download/windows
2. Run installer
3. Open terminal and pull the model:

```bash
ollama pull hermes3
```

4. Test it works:

```bash
ollama run hermes3 "Say hello"
```

### 1.2 Install Hermes Agent

```bash
# Install Hermes
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# Reload shell
source ~/.bashrc

# Run setup wizard
hermes setup
```

During setup:
- Model provider: `ollama`
- Model name: `hermes3`
- Accept defaults for other options

### 1.3 Verify Installation

```bash
hermes chat
```

Type "Hello, what can you do?" - you should get a response. Type `exit` to quit.

---

## Phase 2: Set Up Telegram Bot (for approvals)

### 2.1 Create a Telegram Bot

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Name it something like "SimplifyOps Blog Bot"
4. Username: `simplifyops_blog_bot` (must be unique)
5. **Save the bot token** (looks like `123456789:ABCdefGHI...`)

### 2.2 Get Your Chat ID

1. Search for `@userinfobot` on Telegram
2. Start a chat with it
3. It will reply with your user ID (a number like `123456789`)
4. **Save this number**

### 2.3 Configure Hermes

Edit `~/.hermes/.env`:

```bash
# Open in editor
notepad ~/.hermes/.env
```

Add these lines:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
OLLAMA_BASE_URL=http://localhost:11434
```

Edit `~/.hermes/config.yaml`:

```yaml
model_provider: ollama
model_name: hermes3

telegram:
  enabled: true
  require_approval: true
```

---

## Phase 3: Create Blog Writer Skill

### 3.1 Create Skills Directory

```bash
mkdir -p ~/.hermes/skills
```

### 3.2 Create the Skill File

Create `~/.hermes/skills/blog-writer.md`:

```markdown
---
name: blog-writer
description: Generates SEO blog posts for SimplifyOps
triggers:
  - write blog
  - generate blog post
---

# Blog Writer Skill

## Your Task

Generate an SEO-optimized blog post for simplifyops.co about business operations and automation.

## Steps

1. **Research current trends**
   - Search web for "business operations trends 2026"
   - Search for "small business automation"
   - Pick the most relevant trending topic

2. **Generate the post**
   - Title: SEO-friendly, under 60 characters
   - Length: 800-1200 words
   - Tone: Professional but approachable
   - Structure:
     * Attention-grabbing intro (the problem)
     * Why this matters now
     * 3-5 actionable steps or insights
     * Conclusion with soft CTA ("need help with operations? get in touch")

3. **Format for Jekyll**
   ```yaml
   ---
   layout: post
   title: "Your Title Here"
   date: YYYY-MM-DD
   categories: [operations, automation]
   description: "Meta description under 160 chars"
   ---

   Post content here...
   ```

4. **Save draft**
   - Write to: `~/simplifyops-site/blog/posts/draft-YYYY-MM-DD.md`

5. **Request approval via Telegram**
   - Send message with: title, word count, key points
   - Wait for "approve" or "revise: feedback"

6. **After approval**
   - Rename draft to final: `YYYY-MM-DD-slug.md`
   - Git add, commit, push to origin main

## Important

- Keep content generic - NO personal information
- NO client names or specific project details
- Focus on general expertise and actionable advice
```

---

## Phase 4: Set Up GitHub Repository

### 4.1 Clone Your Site Repo

```bash
cd ~
git clone https://github.com/allavallc/simplifyops-site.git
```

### 4.2 Configure Git Credentials

```bash
cd ~/simplifyops-site
git config user.name "Your Name"
git config user.email "your-github-email@example.com"
```

For pushing, either:
- Use GitHub CLI: `gh auth login`
- Or set up SSH keys
- Or use a Personal Access Token

---

## Phase 5: Schedule Weekly Runs (Windows Task Scheduler)

### 5.1 Create a Run Script

Create `~/.hermes/run-blog-writer.bat`:

```batch
@echo off
cd %USERPROFILE%
hermes run --skill blog-writer "Generate this week's blog post about business operations trends. Research current topics, write an SEO post, send to Telegram for my approval, then publish after I approve."
```

### 5.2 Set Up Task Scheduler

1. Open Task Scheduler (search in Start menu)
2. Click "Create Task" (not Basic Task)

**General tab:**
- Name: `SimplifyOps Blog Generator`
- Check: "Run whether user is logged on or not"

**Triggers tab:**
- New trigger
- Weekly, Monday, 9:00 AM
- Check: "Enabled"

**Settings tab (important for sleep/wake):**
- Check: "Run task as soon as possible after a scheduled start is missed"
- This makes it run when you open your laptop if it was asleep

**Actions tab:**
- New action
- Action: Start a program
- Program: `C:\Users\YOUR_USERNAME\.hermes\run-blog-writer.bat`

3. Click OK, enter your Windows password if prompted

---

## Phase 6: Test Everything

### 6.1 Test Hermes Manually

```bash
hermes chat --skill blog-writer
```

Say: "Generate a short test blog post about productivity"

Verify it:
- Generates content
- Sends to your Telegram
- Responds to your approval

### 6.2 Test the Scheduled Task

1. In Task Scheduler, right-click your task
2. Click "Run"
3. Check Telegram for the draft
4. Reply "approve" or "cancel"

### 6.3 Verify GitHub Pages

After approving, check:
- The commit appeared in your repo
- GitHub Pages deployed (Settings > Pages)
- Post is live at simplifyops.co/blog/

---

## Troubleshooting

### Ollama not responding
```bash
# Check if running
ollama list

# Restart it
ollama serve
```

### Hermes can't find skill
```bash
# Verify skill exists
cat ~/.hermes/skills/blog-writer.md

# Check Hermes sees it
hermes skills list
```

### Telegram not receiving messages
- Verify bot token and chat ID in `~/.hermes/.env`
- Make sure you've started a chat with your bot first
- Send `/start` to your bot in Telegram

### Task didn't run after sleep
- Open Task Scheduler
- Check "History" tab for your task
- Verify "Run task as soon as possible..." is checked

---

## Quick Reference

| Command | What it does |
|---------|--------------|
| `ollama serve` | Start Ollama (if not running) |
| `hermes chat` | Interactive chat mode |
| `hermes chat --skill blog-writer` | Chat with specific skill |
| `hermes run "prompt"` | One-off task |
| `hermes skills list` | Show available skills |
| `hermes gateway start` | Start Telegram listener |

---

## Next Steps After Setup

1. **First week**: Run manually, verify quality
2. **Second week**: Let scheduler run, monitor results
3. **Later**: Consider upgrading to Claude API for better posts
4. **Optional**: Add LinkedIn/Twitter auto-posting
