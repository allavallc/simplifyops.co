# Starting Up SimplifyOps Tools

## Prerequisites
- Laptop plugged in (better performance)
- Power mode set to "Best Performance"

---

## Step 1: Start Ollama

Ollama should auto-start with Windows. Check the system tray for the Ollama icon.

If not running, open the Ollama app from Start menu.

---

## Step 2: Start Hermes

1. Open **PowerShell**
2. Run:
```powershell
hermes chat --model hermes3:3b
```

(Use `hermes3` for better quality but slower, `hermes3:3b` for faster)

**Or** if you set up the shortcut:
```powershell
hchat
```

---

## Step 3: Start Paperclip

1. Open **PowerShell as Administrator**
   - Right-click PowerShell → "Run as administrator"
2. Run:
```powershell
npx paperclipai run
```
3. Open browser to: http://localhost:3100

---

## Quick Reference

| Tool | Command | Port |
|------|---------|------|
| Ollama | (auto-starts) | 11434 |
| Hermes | `hermes chat --model hermes3:3b` | - |
| Paperclip | `npx paperclipai run` | 3100 |

---

## Stopping

- **Hermes**: Type `exit` or press `Ctrl+C`
- **Paperclip**: Press `Ctrl+C` in the PowerShell window
- **Ollama**: Right-click tray icon → Quit

---

## Troubleshooting

**Hermes is slow:**
- Make sure laptop is plugged in
- Set power mode to "Best Performance"
- Use smaller model: `hermes3:3b`

**Paperclip symlink error:**
- Run PowerShell as Administrator

**Hermes uses wrong model:**
- Always include `--model hermes3:3b` flag
