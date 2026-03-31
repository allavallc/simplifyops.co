# SimplifyOps.co

Automated SEO blog engine for simplifyops.co using Hermes Agent.

## Quick Start

**All commands run in WSL.**

### First-time setup

```bash
# Create startup script
cat > ~/start-simplifyops.sh << 'EOF'
#!/bin/bash
cd /mnt/c/Users/adefilippo/MyDocuments/17_projects/brain_business
echo "Starting SimplifyOps with Hermes..."
hermes chat
EOF
chmod +x ~/start-simplifyops.sh
```

### Daily use

```bash
~/start-simplifyops.sh
```

## Architecture

```
brain_business/          # Knowledge base
├── roles/
│   ├── ceo/             # Approves content
│   ├── coo/             # Domain expertise
│   └── content-manager/ # Writes blog posts
│       ├── README.md    # Role instructions
│       └── learnings.md # Updated after feedback

simplifyOps.co/          # Website (GitHub Pages)
├── index.html           # Landing page
├── blog/                # Blog posts
└── contact/             # Contact form
```

## Workflow

1. Run `~/start-simplifyops.sh`
2. Ask Hermes to write a blog post
3. Review the draft
4. Approve or give feedback
5. Hermes updates learnings.md
6. Push to GitHub to publish

## Future

- Add Paperclip orchestration (HS-style with Docker)
- Telegram approval workflow
- Automated weekly publishing
