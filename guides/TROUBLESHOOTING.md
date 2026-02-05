# Auto Claude Troubleshooting Guide

This guide provides solutions to common issues encountered when using Auto Claude. For general usage, see [CLI-USAGE.md](CLI-USAGE.md).

## Quick Links

- [OAuth & Authentication Issues](#oauth--authentication-issues)
- [Git Worktree Issues](#git-worktree-issues)
- [QA Loop & Validation Issues](#qa-loop--validation-issues)
- [Memory System (Graphiti) Issues](#memory-system-graphiti-issues)
- [Platform-Specific Issues](#platform-specific-issues)
- [Common Errors](#common-errors)
- [FAQ](#faq)

---

## OAuth & Authentication Issues

### OAuth Token Expired or Invalid

**Symptoms:**
```
Error: Authentication failed
Error: Invalid OAuth token
401 Unauthorized
```

**Solution:**

Refresh your OAuth token using the Claude Code CLI:

```bash
# Re-authenticate with Claude Code
claude setup-token

# Verify token is stored correctly
# macOS: Keychain Access
# Windows: Credential Manager → Windows Credentials
# Linux: Run `secret-tool search service claude-code`
```

**Alternative:** Set token explicitly in `.env`:

```bash
cd apps/backend
echo "CLAUDE_CODE_OAUTH_TOKEN=your-token-here" >> .env
```

### Encrypted Token Error

**Symptoms:**
```
Error: Authentication token is in encrypted format and cannot be used.
The token decryption process failed or was not attempted.
```

**Cause:** Auto Claude found an encrypted token (`enc:...`) but couldn't decrypt it from the system keychain.

**Solution:**

**Option 1 (Recommended):** Re-authenticate:
```bash
claude setup-token
```

**Option 2:** Set plaintext token in `.env`:
```bash
cd apps/backend
# Get token from Claude Code CLI
claude setup-token --print

# Add to .env
echo "CLAUDE_CODE_OAUTH_TOKEN=your-plaintext-token" >> .env
```

### Token Not Found

**Symptoms:**
```
Error: CLAUDE_CODE_OAUTH_TOKEN not found
Error: No authentication token available
```

**Cause:** No token in environment variables or system keychain.

**Solution:**

**Linux users:** Install `secretstorage` for keychain support:
```bash
pip install secretstorage
```

**All platforms:** Set token in `.env`:
```bash
cd apps/backend
cp .env.example .env
# Get token
claude setup-token --print
# Add to .env: CLAUDE_CODE_OAUTH_TOKEN=your-token
```

### ANTHROPIC_API_KEY Not Supported

**Symptoms:**
```
Warning: ANTHROPIC_API_KEY detected but not used
Auto Claude requires Claude Code OAuth tokens
```

**Cause:** Auto Claude intentionally does NOT support direct API keys to prevent silent billing to your API credits.

**Solution:**

Use Claude Code OAuth authentication instead:
```bash
claude setup-token
```

For enterprise/proxy setups (CCR), use `ANTHROPIC_AUTH_TOKEN`:
```bash
# In apps/backend/.env
ANTHROPIC_AUTH_TOKEN=sk-zcf-x-ccr
ANTHROPIC_BASE_URL=http://your-proxy-url
```

---

## Git Worktree Issues

### Worktree Already Exists

**Symptoms:**
```
Error: Worktree already exists at .auto-claude/worktrees/tasks/001-feature
Error: Branch 'auto-claude/001-feature' already exists
```

**Cause:** Previous build wasn't cleaned up properly, or you're trying to run the same spec twice.

**Solution:**

**Option 1:** Review and merge existing worktree:
```bash
cd apps/backend
python run.py --spec 001 --review
python run.py --spec 001 --merge
```

**Option 2:** Discard the worktree:
```bash
cd apps/backend
python run.py --spec 001 --discard
```

**Option 3:** Manual cleanup (if commands fail):
```bash
# Remove worktree
git worktree remove .auto-claude/worktrees/tasks/001-feature --force

# Delete branch
git branch -D auto-claude/001-feature

# Clean up directory if it still exists
rm -rf .auto-claude/worktrees/tasks/001-feature
```

### Worktree Locked

**Symptoms:**
```
Error: '.git/worktrees/xxx' is locked
fatal: 'xxx' is already checked out
```

**Cause:** Git worktree lock file wasn't cleaned up (crash, Ctrl+C during operation).

**Solution:**

Remove the lock file manually:

**Unix/macOS:**
```bash
rm .git/worktrees/tasks-001-feature/locked
git worktree prune
```

**Windows:**
```powershell
del .git\worktrees\tasks-001-feature\locked
git worktree prune
```

### Merge Conflicts After Worktree Merge

**Symptoms:**
```
Error: Merge conflicts detected
CONFLICT (content): Merge conflict in src/file.js
```

**Solution:**

Auto Claude creates a clean worktree, but conflicts can occur if your main branch changed during the build.

```bash
# Check conflict status
git status

# Option 1: Resolve conflicts manually
# Edit conflicted files, then:
git add .
git commit -m "Resolve merge conflicts from auto-claude/001-feature"

# Option 2: Abort and rebuild
git merge --abort
cd apps/backend
python run.py --spec 001 --discard
# Update your main branch, then rerun
python run.py --spec 001
```

### Detached HEAD in Worktree

**Symptoms:**
```
Warning: You are in 'detached HEAD' state
```

**Solution:**

This shouldn't happen with Auto Claude worktrees. If it does:

```bash
cd .auto-claude/worktrees/tasks/001-feature
git checkout auto-claude/001-feature
```

If branch doesn't exist, the worktree is corrupt. Discard and rebuild:
```bash
cd apps/backend
python run.py --spec 001 --discard
python run.py --spec 001
```

---

## QA Loop & Validation Issues

### QA Loop Exceeds Max Iterations

**Symptoms:**
```
ERROR: QA validation exceeded maximum iterations (50)
Human intervention required
```

**Cause:** The QA Fixer couldn't resolve issues after 50 attempts. This usually means:
- Test setup is broken
- Acceptance criteria are unclear or impossible
- Recurring issues that need architectural changes

**Solution:**

**Step 1:** Check the QA report:
```bash
cd apps/backend
cat .auto-claude/specs/001-feature/qa_report.md
```

**Step 2:** Look for recurring issues:
```bash
python run.py --spec 001 --qa-status
```

**Step 3:** Manual intervention:
```bash
# Navigate to worktree
cd .auto-claude/worktrees/tasks/001-feature

# Fix the issues manually
# Run tests to verify
npm test  # or your test command

# Commit fixes
git add .
git commit -m "Manual QA fixes"

# Merge back
cd apps/backend
python run.py --spec 001 --merge
```

### QA Reports "No Tests Found"

**Symptoms:**
```
Warning: No test files found in project
Skipping test execution
```

**Cause:** Your project doesn't have tests, or test discovery failed.

**Solution:**

**For projects without tests:**
This is expected. QA validation will focus on manual verification of acceptance criteria.

**For projects with tests:**
Check that test files match expected patterns:

| Framework | Expected Patterns |
|-----------|------------------|
| Jest | `*.test.js`, `*.spec.js`, `__tests__/*.js` |
| Pytest | `test_*.py`, `*_test.py`, `tests/` |
| Go | `*_test.go` |
| Rust | `tests/` directory, `#[test]` in `*.rs` |

If tests exist but aren't found, verify test command in `package.json`, `pyproject.toml`, etc.

### Recurring Issues in QA Loop

**Symptoms:**
```
ERROR: Recurring issue detected (3+ occurrences)
Issue: "TypeError: Cannot read property 'x' of undefined"
Escalating to human
```

**Cause:** The same issue keeps reappearing after fixes. This indicates:
- The fix is incomplete or wrong
- There's a deeper architectural issue
- External dependency problem

**Solution:**

**Step 1:** Review the issue history:
```bash
cd apps/backend
python run.py --spec 001 --qa-status
```

**Step 2:** Check the root cause:
```bash
cd .auto-claude/worktrees/tasks/001-feature
# Run tests to see the actual error
npm test
# Or check logs
cat .auto-claude/specs/001-feature/coder-session.log
```

**Step 3:** Manual fix (see "QA Loop Exceeds Max Iterations" above)

### QA Validation Hangs

**Symptoms:**
- QA agent runs for 30+ minutes
- No visible progress
- High CPU usage

**Solution:**

**Step 1:** Interrupt gracefully:
```bash
Ctrl+C (once)  # Pause after current session
```

**Step 2:** Check the session log:
```bash
cd apps/backend
tail -f .auto-claude/specs/001-feature/qa-reviewer-session.log
```

**Step 3:** Common causes and fixes:

| Cause | Solution |
|-------|----------|
| Large test suite | Add `--skip-qa` and test manually |
| Network timeout | Check `ANTHROPIC_BASE_URL` connectivity |
| Infinite loop in tests | Fix tests before running QA |
| Memory leak in tests | Increase system resources or skip QA |

---

## Memory System (Graphiti) Issues

### Graphiti Provider Configuration Error

**Symptoms:**
```
Error: GRAPHITI_LLM_PROVIDER not configured
Error: OPENAI_API_KEY required for OpenAI provider
```

**Cause:** Graphiti memory system is enabled but provider credentials are missing.

**Solution:**

**Option 1 (Recommended):** Disable Graphiti if you don't need it:
```bash
cd apps/backend
echo "GRAPHITI_ENABLED=false" >> .env
```

**Option 2:** Configure provider credentials:

**OpenAI (default):**
```bash
# In apps/backend/.env
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=openai
GRAPHITI_EMBEDDER_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

**Anthropic + Voyage (recommended for Claude users):**
```bash
# In apps/backend/.env
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=anthropic
GRAPHITI_EMBEDDER_PROVIDER=voyage
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
```

**Ollama (local, free):**
```bash
# In apps/backend/.env
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=ollama
GRAPHITI_EMBEDDER_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=deepseek-r1:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

See `.env.example` for complete provider options.

### Graphiti Database Path Error

**Symptoms:**
```
Error: Cannot create Graphiti database at ~/.auto-claude/memories
PermissionError: [Errno 13] Permission denied
```

**Solution:**

**Option 1:** Fix permissions:
```bash
# Unix/macOS
mkdir -p ~/.auto-claude/memories
chmod 755 ~/.auto-claude/memories

# Windows
mkdir %USERPROFILE%\.auto-claude\memories
```

**Option 2:** Use custom path:
```bash
# In apps/backend/.env
GRAPHITI_DB_PATH=/path/to/writable/directory
```

### Python 3.12+ Required for Graphiti

**Symptoms:**
```
Error: Graphiti requires Python 3.12 or higher
Current version: 3.11.x
```

**Cause:** Graphiti uses LadybugDB, which requires Python 3.12+.

**Solution:**

**Option 1 (Recommended):** Disable Graphiti:
```bash
# In apps/backend/.env
GRAPHITI_ENABLED=false
```

**Option 2:** Upgrade Python:

**Windows:**
```bash
winget install Python.Python.3.12
```

**macOS:**
```bash
brew install python@3.12
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install python3.12 python3.12-venv
```

Then recreate your virtual environment:
```bash
cd apps/backend
rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Graphiti Memory Corruption

**Symptoms:**
```
Error: Failed to load Graphiti database
Error: Graph schema mismatch
```

**Solution:**

Reset the Graphiti database:

```bash
# Backup old database (optional)
mv ~/.auto-claude/memories ~/.auto-claude/memories.backup

# Let Auto Claude recreate it
cd apps/backend
python run.py --spec 001
```

---

## Platform-Specific Issues

### Windows: Git Bash Not Found

**Symptoms:**
```
Error: Git Bash not found
Error: claude command not found
```

**Solution:**

Auto Claude needs Git Bash for Unix-like commands on Windows.

**Option 1:** Install Git for Windows (includes Git Bash):
```bash
winget install Git.Git
```

**Option 2:** Tell Auto Claude where Git Bash is:
```bash
# In apps/backend/.env
CLAUDE_CODE_GIT_BASH_PATH=C:\Program Files\Git\bin\bash.exe
```

**Verify installation:**
```bash
# Should open Git Bash
"C:\Program Files\Git\bin\bash.exe"
```

### Windows: Path Too Long

**Symptoms:**
```
Error: Filename too long
OSError: [WinError 206] The filename or extension is too long
```

**Cause:** Windows has a 260-character path limit (even on Windows 10+).

**Solution:**

Enable long paths in Windows:

**Option 1:** Group Policy (Windows Pro/Enterprise):
1. Press `Win+R`, type `gpedit.msc`, press Enter
2. Navigate to: Computer Configuration → Administrative Templates → System → Filesystem
3. Enable "Enable Win32 long paths"
4. Restart

**Option 2:** Registry (all Windows versions):
```powershell
# Run as Administrator
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

**Option 3:** Move project to shorter path:
```bash
# Instead of: C:\Users\YourName\Documents\Projects\auto-claude-workspace\...
# Use: C:\dev\auto-claude\...
```

### macOS: Command Not Found After Install

**Symptoms:**
```
zsh: command not found: claude
zsh: command not found: python3
```

**Solution:**

**For Homebrew installations:**
```bash
# Intel Mac
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc

# Apple Silicon (M1/M2/M3)
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc

# Reload shell
source ~/.zshrc
```

**For Python:**
```bash
# Install Python 3.12 via Homebrew
brew install python@3.12

# Link it
brew link python@3.12
```

### Linux: Secret Service Not Available

**Symptoms:**
```
Warning: secretstorage not available
Cannot access system keychain
```

**Cause:** Linux keychain support requires `secretstorage` Python package and DBus.

**Solution:**

**Install secretstorage:**
```bash
cd apps/backend
source .venv/bin/activate
pip install secretstorage
```

**If DBus is missing (headless servers):**

Disable keychain and use environment variables:
```bash
# In apps/backend/.env
CLAUDE_CODE_OAUTH_TOKEN=your-token-here
```

---

## Common Errors

### Module Not Found

**Symptoms:**
```
ModuleNotFoundError: No module named 'anthropic'
ModuleNotFoundError: No module named 'graphiti_core'
```

**Solution:**

Reinstall dependencies:
```bash
cd apps/backend

# Using uv (recommended)
uv pip install -r requirements.txt

# Or using pip
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Spec Not Found

**Symptoms:**
```
Error: Spec not found: 001
Error: Spec directory does not exist: .auto-claude/specs/001-feature
```

**Solution:**

**List all specs:**
```bash
cd apps/backend
python run.py --list
```

**Create a new spec:**
```bash
python runners/spec_runner.py --interactive
```

**Check spec directory:**
```bash
ls -la .auto-claude/specs/
```

### Permission Denied

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: '.auto-claude/specs/001/spec.md'
```

**Solution:**

**Fix permissions:**
```bash
# Unix/macOS
chmod -R 755 .auto-claude

# Windows (run as Administrator)
icacls .auto-claude /grant Users:F /t
```

**Check file ownership:**
```bash
ls -la .auto-claude/specs/001/
# Files should be owned by your user
```

### Git Remote Not Set

**Symptoms:**
```
Warning: No git remote found
Warning: Cannot push to remote
```

**Cause:** Your project isn't connected to a Git remote (GitHub, GitLab, etc.).

**Solution:**

This is a warning, not an error. Auto Claude can still work locally.

**To add a remote:**
```bash
# For GitHub
git remote add origin https://github.com/username/repo.git

# For GitLab
git remote add origin https://gitlab.com/username/repo.git

# Verify
git remote -v
```

---

## FAQ

### How do I reset everything and start fresh?

```bash
# 1. Discard all worktrees
cd apps/backend
python run.py --spec 001 --discard
python run.py --spec 002 --discard

# 2. Remove all specs
rm -rf .auto-claude/

# 3. Reset Python environment
rm -rf apps/backend/.venv
cd apps/backend
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# 4. Re-authenticate
claude setup-token
```

### Can I run multiple specs in parallel?

Yes! Each spec gets its own isolated worktree:

```bash
# Terminal 1
cd apps/backend
python run.py --spec 001

# Terminal 2
cd apps/backend
python run.py --spec 002
```

### How do I pause a running build?

**Option 1:** Interrupt gracefully (waits for current session to finish):
```bash
Ctrl+C (once)
```

**Option 2:** File-based pause (for automation):
```bash
touch .auto-claude/specs/001-feature/PAUSE
```

**Option 3:** Force stop (may corrupt session):
```bash
Ctrl+C (twice)
```

### How do I add instructions mid-build?

**While paused:**
```bash
Ctrl+C  # Pause
# Edit this file:
echo "Focus on the authentication module first" > .auto-claude/specs/001-feature/HUMAN_INPUT.md
# Resume (just run again)
cd apps/backend
python run.py --spec 001
```

### Can I use Auto Claude without Claude Code CLI?

No. Auto Claude is built on the Claude Agent SDK, which requires Claude Code OAuth authentication. However, for enterprise setups, you can use a proxy:

```bash
# In apps/backend/.env
ANTHROPIC_AUTH_TOKEN=your-ccr-token
ANTHROPIC_BASE_URL=http://your-proxy-url
```

### How do I check my credit usage?

Auto Claude uses Claude Code credits. Check usage in:
- Claude Code CLI: `claude usage`
- Claude.ai Dashboard: https://claude.ai/settings/billing

### Why is the agent stuck on one subtask?

**Common causes:**
1. **Test failures** - Check `coder-session.log` for test output
2. **Infinite loop** - Agent is retrying the same fix repeatedly
3. **Network issues** - Check internet connection and `ANTHROPIC_BASE_URL`
4. **Large files** - Agent processing very large files (>10k lines)

**Solution:** Pause (`Ctrl+C`) and check logs:
```bash
cd apps/backend
tail -f .auto-claude/specs/001-feature/coder-session.log
```

### Can I customize the QA criteria?

Yes! Edit the spec before running:

```bash
# Edit acceptance criteria
nano .auto-claude/specs/001-feature/spec.md

# Then run the build
cd apps/backend
python run.py --spec 001
```

### How do I report a bug?

1. **Check existing issues:** https://github.com/OBenner/Auto-Coding/issues
2. **Collect debug info:**
   ```bash
   cd apps/backend
   # Enable debug mode
   echo "DEBUG=true" >> .env
   echo "DEBUG_LEVEL=3" >> .env
   # Reproduce the issue
   python run.py --spec 001 2>&1 | tee debug.log
   ```
3. **Create a new issue** with:
   - Your OS and Python version
   - The command you ran
   - The error message
   - Debug log (if possible)

### Where can I get help?

- **GitHub Issues:** https://github.com/OBenner/Auto-Coding/issues
- **Discord:** [Auto Claude Community](https://discord.gg/auto-claude) *(check README for current invite)*
- **Documentation:** https://github.com/OBenner/Auto-Coding/tree/main/guides

---

## Additional Resources

- **[CLI Usage Guide](CLI-USAGE.md)** - Complete CLI command reference
- **[Spec Creation Pipeline](SPEC-CREATION-PIPELINE.md)** - Deep dive into spec creation
- **[Windows Development Guide](windows-development.md)** - Windows-specific development tips
- **[Linux Guide](linux.md)** - Linux installation and build instructions
- **[Contributing](../CONTRIBUTING.md)** - How to contribute to Auto Claude

---

*Last updated: 2026-02-01*
