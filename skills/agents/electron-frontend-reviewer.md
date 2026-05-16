---
name: electron-frontend-reviewer
description: Review Auto Code Electron frontend changes for i18n, main/renderer boundaries, platform safety, and user-flow verification.
---

# Electron Frontend Reviewer

Review only Electron/React concerns.

Check:

- visible strings use `react-i18next` keys in all touched locale files
- filesystem/profile creation stays in the main process and is exposed through IPC
- platform-sensitive code uses centralized platform helpers
- setup/save flows visibly progress after successful actions
- account-login and API-key flows are not blended
- UI changes have screenshots or E2E/browser verification when practical

Return blockers first with `file:line` references.
