# Cloud-Hosted Auto Code - Overview

**A fully managed cloud deployment of Auto Code where users can access autonomous AI agents without local installation.**

---

## Table of Contents

- [What is Cloud-Hosted Auto Code?](#what-is-cloud-hosted-auto-code)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Key Features](#key-features)
- [Use Cases](#use-cases)
- [Deployment Models](#deployment-models)
- [User Experience](#user-experience)
- [Security & Privacy](#security--privacy)
- [Comparison: Cloud vs Local](#comparison-cloud-vs-local)
- [Getting Started](#getting-started)
- [Technical Documentation](#technical-documentation)

---

## What is Cloud-Hosted Auto Code?

Cloud-Hosted Auto Code is a web-based deployment of the Auto Code autonomous coding framework that runs entirely in the cloud. Users access it through a web browser without installing any software locally.

**Key Concept:** Instead of downloading and running Auto Code on your local machine, you connect to a centrally hosted instance where all the AI agents, code generation, and build processes happen in the cloud.

### Why Cloud-Hosted?

- **Zero Setup** - No installation, dependencies, or configuration required
- **Instant Access** - Sign up and start building in minutes
- **Team Collaboration** - Multiple users can access the same cloud instance
- **Scalable Resources** - Cloud infrastructure scales automatically based on demand
- **Centralized Management** - One place to manage users, permissions, and usage
- **Always Updated** - Cloud deployments stay on the latest version automatically

---

## How It Works

### User Workflow

```
1. User signs up → 2. Connects GitHub/GitLab → 3. Creates build tasks → 4. AI agents execute → 5. Changes merged
```

**Step-by-Step:**

1. **Sign Up**
   - User creates an account with email/password
   - Account is created in the cloud database
   - User receives access to the web dashboard

2. **Connect Git Repository**
   - User authorizes Auto Code via OAuth (GitHub or GitLab)
   - OAuth tokens are stored securely (encrypted at rest)
   - Auto Code can now read/write to the user's repositories

3. **Create Build Tasks**
   - User describes what they want built (e.g., "Add user authentication")
   - Task specification is stored in the cloud database
   - Build is queued for execution

4. **AI Agents Execute**
   - Cloud-hosted AI agents (Claude) analyze the codebase
   - Agents create implementation plans and write code
   - All code generation happens in isolated cloud workspaces
   - QA validation runs automatically

5. **Changes Applied**
   - Generated code is committed to a branch in the user's repository
   - User reviews the changes via GitHub/GitLab pull request
   - User merges the pull request when satisfied

---

## Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         User's Browser                            │
│                       (React Web Frontend)                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTPS/WebSocket
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Cloud Infrastructure                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Web Backend   │  │  PostgreSQL  │  │    Redis     │        │
│  │    (FastAPI)    │◄─┤   Database   │  │   (Cache)    │        │
│  │                 │  │              │  │              │        │
│  │ • Auth/Users    │  │ • Users      │  │ • Sessions   │        │
│  │ • Git OAuth     │  │ • Repos      │  │ • Rate Limit │        │
│  │ • Usage Track   │  │ • Tasks      │  │ • Usage Data │        │
│  └────────┬────────┘  └──────────────┘  └──────────────┘        │
│           │                                                        │
│           ├──► GitHub API (OAuth + Repository Access)            │
│           ├──► GitLab API (OAuth + Repository Access)            │
│           └──► Claude API (AI Agent Execution)                   │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Web Frontend** | User interface for signup, OAuth, task management, usage dashboard | React, TypeScript, Tailwind CSS |
| **Web Backend** | API server handling authentication, OAuth, usage tracking, agent coordination | Python, FastAPI, SQLAlchemy |
| **PostgreSQL** | Persistent storage for users, repositories, tasks, and audit logs | PostgreSQL 16+ |
| **Redis** | Caching, session management, rate limiting, and usage metrics | Redis 7+ |
| **Git Providers** | Repository access via OAuth (GitHub, GitLab) | OAuth 2.0 |
| **Claude API** | AI agent execution (code generation, analysis, QA) | Anthropic Claude API |

---

## Key Features

### 1. Multi-User Authentication

- **Email/Password Registration** - Standard account creation with secure password hashing (bcrypt)
- **Session Management** - Secure sessions with JWT tokens
- **User Profiles** - Each user has their own isolated workspace
- **Account Verification** - Email verification for production deployments

### 2. Git Repository Integration

- **GitHub OAuth** - Connect GitHub accounts for repository access
- **GitLab OAuth** - Connect GitLab accounts for repository access
- **Token Management** - OAuth tokens stored securely with encryption
- **Repository Linking** - Users can link multiple repositories
- **Branch Management** - Auto Code creates branches for each build

### 3. Usage Tracking & Rate Limiting

- **Request Tracking** - Every API call is tracked by user and endpoint
- **Time-Series Data** - Usage metrics stored by hour/day/month
- **Rate Limiting** - Configurable rate limits per user (e.g., 1000 req/hour)
- **Usage Dashboard** - Visual dashboard showing usage trends and statistics
- **Billing Integration Ready** - Usage data can feed into billing systems

### 4. Cloud Infrastructure

- **Docker Support** - Containerized deployment with docker-compose
- **Kubernetes Support** - Production-ready K8s manifests for scalability
- **High Availability** - Multiple replicas, health checks, rolling updates
- **Auto-Scaling** - Horizontal pod autoscaling based on load
- **Load Balancing** - NGINX ingress with SSL/TLS termination

### 5. Security & Compliance

- **Encrypted Secrets** - OAuth tokens and API keys encrypted at rest
- **TLS/SSL** - All traffic encrypted in transit (HTTPS)
- **Network Isolation** - Private networks for database and cache
- **Resource Limits** - CPU/memory limits prevent resource exhaustion
- **Audit Logging** - All actions logged for compliance

---

## Use Cases

### Individual Developers

**Scenario:** Developer wants to try Auto Code without installing anything locally.

- Sign up in 2 minutes
- Connect GitHub account
- Start building immediately
- No local environment setup required

**Benefits:**
- Quick evaluation of Auto Code
- No commitment to local installation
- Works from any device with a browser

---

### Small Teams (2-10 developers)

**Scenario:** Startup team wants centralized code generation for their project.

- One cloud deployment for the entire team
- Each developer has their own account
- Shared usage dashboard for monitoring
- Centralized OAuth tokens (no individual Claude API keys needed)

**Benefits:**
- Single place to manage Auto Code access
- Usage visibility across the team
- Simplified billing (one subscription vs. multiple)

---

### Enterprise Organizations (10+ developers)

**Scenario:** Large company wants Auto Code for multiple teams with compliance requirements.

- Deploy to private cloud infrastructure (AWS, GCP, Azure)
- SSO integration for user authentication
- Data residency compliance (e.g., EU data stays in EU)
- Usage quotas per team/department
- Audit logging for security reviews

**Benefits:**
- Meets enterprise security requirements
- Scales to hundreds of users
- Centralized compliance and governance
- Integration with existing identity providers

---

## Deployment Models

### 1. Shared SaaS (Not Yet Available)

**Description:** Anthropic or a third party hosts a multi-tenant cloud instance where all users share the same infrastructure.

**Characteristics:**
- Lowest cost (economies of scale)
- Instant access (just sign up)
- Managed by service provider
- Shared resources with other users

**Status:** This deployment model is not yet publicly available but could be offered in the future.

---

### 2. Dedicated Cloud (Self-Hosted)

**Description:** You deploy and manage your own cloud instance on your infrastructure.

**Characteristics:**
- Full control over infrastructure
- Deploy to your cloud provider (AWS, GCP, Azure, DigitalOcean)
- Private instance (not shared with other organizations)
- You manage updates and scaling

**Status:** ✅ **Available Now** - Documentation and deployment manifests are ready.

**Documentation:**
- [Cloud Setup Guide](CLOUD_SETUP.md) - Initial deployment
- [Cloud Deployment Guide](CLOUD_DEPLOYMENT.md) - Production operations

---

### 3. Hybrid (Cloud Backend + Local Desktop Frontend)

**Description:** Use the cloud backend for multi-user features but access via the local desktop app.

**Characteristics:**
- Desktop app connects to cloud backend instead of local backend
- User interface runs locally, agents execute in cloud
- Best of both worlds (desktop UX + cloud scalability)

**Status:** 🚧 **Future Enhancement** - Not yet implemented.

---

## User Experience

### Web Frontend Features

The cloud-hosted web frontend provides:

1. **Sign Up & Login Pages**
   - Email/password registration
   - Secure authentication
   - Password reset flow (future)

2. **Git Settings Page**
   - OAuth connection buttons for GitHub/GitLab
   - Connected account status
   - Repository management

3. **Usage Dashboard**
   - Today's request count
   - Monthly request count
   - Usage trends chart (recharts visualization)
   - Detailed usage breakdown by time period

4. **Task Management** (Future)
   - Create new build tasks
   - Monitor agent progress in real-time
   - Review generated code
   - Merge to main branch

5. **Cloud Mode Indicator**
   - Badge shows if running in cloud mode (☁️) or local mode (💻)
   - Configurable via environment variable

### API Endpoints

The backend exposes these key APIs:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/users/register` | POST | User registration |
| `/api/users/login` | POST | User authentication |
| `/api/git/github/authorize` | GET | Initiate GitHub OAuth |
| `/api/git/github/callback` | GET | Handle GitHub OAuth callback |
| `/api/git/gitlab/authorize` | GET | Initiate GitLab OAuth |
| `/api/git/gitlab/callback` | GET | Handle GitLab OAuth callback |
| `/api/git/status` | GET | Check OAuth connection status |
| `/api/usage/dashboard` | GET | Get usage summary |
| `/api/usage/stats` | GET | Get detailed usage statistics |
| `/api/usage/health` | GET | Check Redis health |

---

## Security & Privacy

### Data Security

**At Rest:**
- Passwords hashed with bcrypt (cost factor 12)
- OAuth tokens encrypted using Fernet symmetric encryption
- Database backups encrypted
- Redis data stored in memory (optional persistence to encrypted volume)

**In Transit:**
- All traffic over HTTPS (TLS 1.3)
- Certificate management via cert-manager (Let's Encrypt)
- Strict Transport Security (HSTS) headers

### Privacy Considerations

**What Data is Stored:**
- User email and hashed password
- OAuth tokens for GitHub/GitLab (encrypted)
- Repository URLs linked by the user
- API usage statistics (anonymous unless user opts in)
- Task specifications and build logs

**What Data is NOT Stored:**
- Your source code (read from GitHub/GitLab, not stored in cloud DB)
- Claude API responses (not persisted, only temporarily in Redis cache)
- Git commit history (only metadata about branches created)

**Data Retention:**
- User data retained while account is active
- Usage logs retained for 90 days (configurable)
- OAuth tokens revoked when user disconnects account
- Account deletion removes all user data within 30 days

---

## Comparison: Cloud vs Local

| Aspect | Cloud-Hosted | Local Desktop |
|--------|--------------|---------------|
| **Installation** | None (web-based) | Download and install app |
| **Setup Time** | 2-5 minutes | 10-30 minutes |
| **System Requirements** | Any device with browser | Windows/macOS/Linux machine |
| **Updates** | Automatic (always latest) | Manual or auto-update |
| **Team Collaboration** | Built-in multi-user | Each person installs separately |
| **Usage Tracking** | Centralized dashboard | Local logging only |
| **Git Integration** | OAuth (GitHub/GitLab) | Local git CLI |
| **Resource Usage** | Cloud (shared or dedicated) | Local CPU/RAM |
| **Cost Model** | Usage-based (per request) | One-time or subscription |
| **Data Privacy** | Stored in cloud | Stays on local machine |
| **Internet Required** | Yes (always) | Only for Claude API calls |
| **Ideal For** | Teams, enterprises, quick trials | Individual devs, full control |

---

## Getting Started

### For Users (Accessing a Cloud Instance)

If your organization has deployed a cloud instance:

1. **Get the Cloud URL**
   - Example: `https://autoclaude.yourcompany.com`
   - Your admin should provide this

2. **Sign Up**
   - Navigate to `<cloud-url>/signup`
   - Enter email and password
   - Submit registration

3. **Connect Git Account**
   - Navigate to `<cloud-url>/settings/git`
   - Click "Connect GitHub" or "Connect GitLab"
   - Authorize Auto Code to access your repositories

4. **Start Building**
   - Navigate to task creation page (future)
   - Describe what you want to build
   - Monitor agent progress in real-time

---

### For Administrators (Deploying Cloud Instance)

If you want to deploy your own cloud-hosted Auto Code:

**Quick Start (Docker Compose - Development/Small Teams):**

```bash
# 1. Clone the repository
git clone https://github.com/OBenner/Auto-Coding.git
cd Auto-Claude

# 2. Configure environment variables
cd apps/web-backend
cp .env.example .env
# Edit .env with your settings (database URL, OAuth credentials, secret key)

# 3. Start the cloud stack
docker-compose -f docker-compose.cloud.yml up -d

# 4. Run database migrations
docker-compose -f docker-compose.cloud.yml exec web-backend alembic upgrade head

# 5. Access the web interface
# Open browser to http://localhost:8000
```

**Production Deployment (Kubernetes - Scalable/Enterprise):**

See [Cloud Deployment Guide](CLOUD_DEPLOYMENT.md) for:
- Kubernetes manifest configuration
- Production security hardening
- High availability setup
- Monitoring and logging
- Backup and disaster recovery

---

## Technical Documentation

### For Developers & Operators

| Document | Audience | Purpose |
|----------|----------|---------|
| **[CLOUD_SETUP.md](CLOUD_SETUP.md)** | Admins deploying for first time | Initial setup, OAuth config, database init |
| **[CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md)** | DevOps/SREs running production | Deployment methods, scaling, monitoring, troubleshooting |
| **[E2E_TEST_GUIDE.md](../apps/web-backend/tests/E2E_TEST_GUIDE.md)** | QA engineers | End-to-end testing procedures |
| **[tests/README.md](../apps/web-backend/tests/README.md)** | Developers | Test suite overview and CI/CD integration |

### Architecture Deep-Dives

**Database Schema:**
- `users` table - User accounts (id, email, hashed_password, created_at, is_active)
- `repositories` table - Linked Git repos (id, user_id, provider, repository_url, access_token, created_at)

**Migrations:**
- `001_create_users.py` - Initial users table
- `002_create_repositories.py` - Repositories table with foreign key to users

**Services:**
- `UsageTracker` (services/usage_tracker.py) - Redis-based usage tracking with rate limiting
- `GitService` (services/git_service.py) - GitHub/GitLab API integration
- `AgentRunner` (services/agent_runner.py) - Claude API integration for agent execution

**Middleware:**
- `UsageTrackingMiddleware` (core/middleware.py) - Automatic request tracking for all API calls
- `SessionMiddleware` - OAuth state token management

---

## FAQ

### Q: Is cloud-hosted Auto Code available as a SaaS service?

**A:** Not yet. Currently, you can deploy your own cloud instance using the provided deployment guides and infrastructure manifests. A fully managed SaaS offering may be available in the future.

---

### Q: Can I use cloud-hosted Auto Code without connecting GitHub/GitLab?

**A:** Not for the full functionality. Auto Code needs access to your Git repositories to read code, create branches, and commit changes. OAuth integration is required.

---

### Q: How much does cloud-hosted Auto Code cost?

**A:** The software is free (AGPL-3.0 license), but you pay for:
- Cloud infrastructure (compute, storage, bandwidth) via your cloud provider
- Claude API usage (charges from Anthropic based on tokens processed)

For a dedicated cloud deployment on AWS, expect ~$200-500/month for a small team.

---

### Q: Can I deploy cloud-hosted Auto Code to my private cloud?

**A:** Yes! The deployment manifests support any Kubernetes-compatible environment:
- AWS EKS
- Google Cloud GKE
- Azure AKS
- DigitalOcean Kubernetes
- On-premises Kubernetes clusters

---

### Q: Is my code stored in the cloud database?

**A:** No. Your source code is read from GitHub/GitLab via API but not stored in the cloud database. Only metadata (repository URLs, branch names, task descriptions) is stored.

---

### Q: What happens if the cloud instance goes down?

**A:** Your code is safe in your Git repositories. If the cloud instance goes down:
- You lose access to the web dashboard temporarily
- Ongoing builds are interrupted (will need to retry)
- Your source code and Git history are unaffected (they live in GitHub/GitLab)
- Once the instance is back up, you can resume work

---

### Q: Can I migrate from local desktop to cloud-hosted?

**A:** Yes. Your tasks, specs, and codebase are git-based and portable. You can:
1. Deploy a cloud instance
2. Connect the same Git repositories
3. Continue working on the same tasks

Your Git repositories are the source of truth, so switching deployment models is seamless.

---

## Support & Contributing

### Getting Help

- **Documentation Issues** - [Open an issue](https://github.com/OBenner/Auto-Coding/issues) if you find errors or gaps
- **Deployment Questions** - [Join Discord](https://discord.gg/KCXaPBr4Dj) for community support
- **Enterprise Support** - Contact the maintainers for commercial support options

### Contributing

The cloud-hosted feature is open source (AGPL-3.0). Contributions are welcome:

- **Code Contributions** - See [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Documentation Improvements** - Submit PRs to improve these guides
- **Bug Reports** - File issues with reproduction steps
- **Feature Requests** - Discuss in GitHub Discussions

---

## License

Cloud-hosted Auto Code is licensed under **AGPL-3.0** (same as the main Auto Code project).

**What this means:**
- ✅ Free to deploy and use for your team/organization
- ✅ Free to modify and customize
- ⚠️ If you run it as a service for others, you must open source your modifications
- ❌ Cannot create a proprietary closed-source SaaS based on it without commercial license

For closed-source commercial deployments, contact the maintainers about commercial licensing.

---

## Next Steps

Ready to deploy? Choose your path:

- **Quick Trial (Docker Compose)** → [Cloud Setup Guide](CLOUD_SETUP.md)
- **Production Deployment (Kubernetes)** → [Cloud Deployment Guide](CLOUD_DEPLOYMENT.md)
- **Development/Testing** → [E2E Test Guide](../apps/web-backend/tests/E2E_TEST_GUIDE.md)
- **Understand the Code** → [Backend README](../apps/web-backend/README.md)

Have questions? [Join the Discord community](https://discord.gg/KCXaPBr4Dj) or [open a GitHub discussion](https://github.com/OBenner/Auto-Coding/discussions).
