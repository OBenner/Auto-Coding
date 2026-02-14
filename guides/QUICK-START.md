# Quick Start Guide

Get Auto Code running and building your first feature in under 15 minutes.

This guide focuses on the fastest path to success: using the desktop app. For CLI usage, see [CLI Usage Guide](./CLI-USAGE.md).

## What You'll Need

- **A computer** running Windows, macOS, or Linux
- **A git repository** you want to work on (can be empty or existing)
- **Claude Pro or Max subscription** ($20/month or more) for API access

---

## Step 1: Download and Install (2 minutes)

Download the latest release for your platform:

**[Download from GitHub Releases](https://github.com/OBenner/Auto-Coding/releases)**

Install the application like any other desktop app:

- **Windows:** Run the `.exe` installer
- **macOS:** Open the `.dmg` and drag to Applications
- **Linux:** Extract and run the AppImage, or install the `.deb`/`.rpm`

---

## Step 2: Launch and Connect Claude (3 minutes)

When you first open Auto Code, you'll see a welcome screen asking you to connect Claude.

1. Click the **"Connect Claude"** button
2. Your browser opens to Claude's OAuth page
3. Sign in with your Claude account (Pro or Max required)
4. Authorize Auto Code to access Claude
5. Return to the app -- you're connected!

**Why OAuth?** Auto Code uses the official Claude Agent SDK with your account. Your API token is stored securely in your system keychain.

---

## Step 3: Open Your Project (1 minute)

1. Click **"Open Project"** or **"Select Repository"**
2. Navigate to any folder on your computer that contains a git repository
3. Select it and click **"Open"**

Auto Code detects your project stack (Python, Node.js, etc.) and configures security automatically.

---

## Step 4: Create Your First Task (2 minutes)

You're now at the Kanban board. Click **"Create New Spec"** (or the `+` button).

You'll see a form with these fields:

- **Task Description:** Describe what you want in plain English
- **Complexity:** Leave as "Auto-detect" (or choose Simple/Standard/Complex)
- **GitHub Issue (optional):** Paste an issue URL to import it

**Example first task:**

```
Add a dark mode toggle to the settings page that persists user preference
```

Click **"Create Spec"** and watch the agents work.

---

## Step 5: Watch the Agents Build (5 minutes)

The Kanban board shows your task moving through stages:

### Spec Creation (2-3 minutes)
The spec agent asks clarifying questions, creates a structured spec, and defines acceptance criteria. You can interact in the terminal if needed.

### Planning (1 minute)
The planner breaks your spec into implementation subtasks -- each with files to modify, verification steps, and completion criteria.

### Implementation (varies)
The coder agent works through subtasks sequentially. You can:
- Watch multiple terminals work in parallel
- Click any terminal to see full context
- Review changes in real-time

### QA Validation (1-2 minutes)
The QA reviewer validates against acceptance criteria and runs tests. Issues go back to the QA fixer in a loop until all pass.

**What you do:** Nothing! Agents work autonomously. Monitor progress, but don't intervene unless something goes wrong.

---

## Step 6: Review and Merge (2 minutes)

When QA passes, your task moves to **"Ready for Review"**.

1. Click the task card to open review mode
2. See a summary of changes:
   - Files modified
   - New files created
   - Test results
3. Click **"Open in Worktree"** to see the actual code changes
4. Test the feature manually if you want
5. When satisfied, click **"Merge to Main"**

The changes merge cleanly to your branch. Your main branch is never touched until you approve.

---

## What Just Happened?

In about 15 minutes, you:

1. ✅ Installed Auto Code
2. ✅ Connected Claude via OAuth
3. ✅ Opened your git repository
4. ✅ Created a task from plain English
5. ✅ Watched autonomous agents:
   - Create a spec
   - Plan implementation
   - Write the code
   - Run QA tests
6. ✅ Reviewed and merged clean code

**Key point:** Your main branch stayed safe the entire time. All work happened in an isolated git worktree.

---

## Next Steps

Now that you've completed your first task, explore:

- **[CLI Usage Guide](./CLI-USAGE.md)** -- Terminal workflows and CI/CD integration
- **[Spec Creation Pipeline](./SPEC-CREATION-PIPELINE.md)** -- Deep dive on how specs are created
- **[Troubleshooting](./TROUBLESHOOTING.md)** -- Common issues and fixes
- **[Intelligent Pattern Recognition](./INTELLIGENT-PATTERN-RECOGNITION.md)** -- How agents learn from previous builds

---

## Tips for Faster Workflows

### Start Simple
Your first task should be straightforward -- a new feature, bug fix, or refactor. Save complex multi-file changes for after you've seen the system work.

### Use Specific Descriptions
Instead of:
```
Fix the login
```

Use:
```
Fix the login form validation to show inline error messages when email is invalid
```

### Let Agents Work
Don't intervene unless agents are stuck or asking questions. The QA loop catches most issues.

### Review Before Merging
Always check the worktree before merging. Agents are good, but you're the final reviewer.

---

## Common Questions

**Do I need to be a developer?**
Yes, Auto Code is for developers. It writes code for you, but you should understand your codebase.

**Can it work with any language?**
Yes, but it works best with popular languages (Python, JavaScript/TypeScript, Go, Rust, Java).

**What if agents get stuck?**
The recovery agent automatically detects stuck agents and tries alternative approaches. You can also manually intervene in the terminal.

**Is my code safe?**
Yes. Three-layer security: OS sandbox, filesystem restrictions, and dynamic command allowlisting based on your project stack.

**How much does it cost?**
Auto Code is free (AGPL-3.0). You pay Claude for API usage based on your Pro/Max plan. Typical tasks cost $0.10-$1.00 in API credits.

---

## Getting Help

- **[Discord Community](https://discord.gg/KCXaPBr4Dj)** -- Chat with other users, get help
- **[GitHub Issues](https://github.com/OBenner/Auto-Coding/issues)** -- Report bugs or request features
- **[GitHub Discussions](https://github.com/OBenner/Auto-Coding/discussions)** -- Ask questions, share ideas

---

Ready? Go build something amazing.
