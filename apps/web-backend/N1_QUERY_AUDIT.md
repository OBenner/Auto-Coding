# N+1 Query Audit Report
**Web-Backend Database Query Analysis**

**Date:** 2026-02-25
**Auditor:** Auto-Claude Performance Optimization Agent
**Scope:** All API routes in `apps/web-backend/api/routes/`

---

## Executive Summary

**Finding:** ✅ **NO N+1 QUERY PATTERNS DETECTED**

The web-backend codebase is currently free of N+1 query anti-patterns. This is primarily because:
1. The application architecture uses file-system based operations for specs/tasks (not database queries)
2. Database usage is minimal and limited to simple user authentication queries
3. No route currently fetches related objects (e.g., user repositories with user data)

**Risk Level:** 🟢 **LOW** - Current implementation has no N+1 queries
**Recommendation:** Document best practices for future development to prevent N+1 patterns as features grow

---

## Database Schema Overview

### Models with Relationships

| Model | Table | Relationships | Notes |
|-------|-------|---------------|-------|
| `User` | `users` | `repositories` (one-to-many) | User has many GitRepository |
| `GitRepository` | `repositories` | `user` (many-to-one) | Belongs to User |

### Existing Indexes

| Table | Column | Type | Status |
|-------|--------|------|--------|
| `users` | `id` | PRIMARY KEY | ✅ Indexed |
| `users` | `email` | UNIQUE | ✅ Indexed |
| `repositories` | `id` | PRIMARY KEY | ✅ Indexed |
| `repositories` | `user_id` | FOREIGN KEY | ✅ Indexed |

---

## Route-by-Route Analysis

### 1. `/api/users` (users.py)

**Endpoints:**
- `POST /api/users/register` - User registration
- `POST /api/users/login` - User login

**Queries:**
```python
# Single query by email - no N+1 issue
db.query(User).filter(User.email == request.email).first()
```

**Analysis:** ✅ **OPTIMAL**
- Simple single-record queries
- No relationship loading needed
- Uses indexed `email` column

---

### 2. `/api/git` (git.py)

**Endpoints:**
- `GET /api/git/github/authorize` - GitHub OAuth flow
- `GET /api/git/github/callback` - GitHub OAuth callback
- `GET /api/git/gitlab/authorize` - GitLab OAuth flow
- `GET /api/git/gitlab/callback` - GitLab OAuth callback

**Queries:** None (OAuth flow, no database access)

**Analysis:** ✅ **OPTIMAL** - No database queries

---

### 3. `/api/agents` (agents.py)

**Endpoints:**
- `POST /api/agents/run` - Start agent execution
- `GET /api/agents/status/{task_id}` - Get agent status
- `POST /api/agents/cancel/{task_id}` - Cancel agent execution

**Queries:** None (uses service layer with in-memory state)

**Analysis:** ✅ **OPTIMAL** - No database queries

---

### 4. `/api/specs` (specs.py)

**Endpoints:**
- `GET /api/specs` - List all specs
- `GET /api/specs/{spec_id}` - Get spec details

**Queries:** None (file-system based operations)

**Analysis:** ✅ **OPTIMAL** - Uses file system for spec storage

---

### 5. `/api/tasks` (tasks.py)

**Endpoints:**
- `GET /api/tasks` - List all tasks
- `GET /api/tasks/{task_id}` - Get task details

**Queries:** None (file-system based operations)

**Analysis:** ✅ **OPTIMAL** - Uses file system for task storage

---

### 6. `/api/usage` (usage.py)

**Endpoints:**
- `GET /api/usage/stats` - Get usage statistics
- `GET /api/usage/dashboard` - Get usage dashboard
- `GET /api/usage/health` - Health check

**Queries:** None (Redis-based usage tracking)

**Analysis:** ✅ **OPTIMAL** - Uses Redis for analytics

---

### 7. `/api/auth` (auth.py)

**Endpoints:**
- `POST /api/auth/verify` - Verify JWT token

**Queries:** None (JWT validation, no database access)

**Analysis:** ✅ **OPTIMAL** - Stateless JWT authentication

---

## Potential N+1 Scenarios (Future Features)

The following N+1 patterns **could occur** if new features are added without proper eager loading:

### Scenario 1: List User Repositories (High Risk)

**Hypothetical Anti-Pattern:**
```python
# ❌ BAD - Would cause N+1 query
@router.get("/users/{user_id}/repositories")
async def list_user_repositories(user_id: int, db: Session = Depends(get_db)):
    repositories = db.query(GitRepository).filter_by(user_id=user_id).all()

    # N+1: Accessing user.email for each repository triggers separate query
    result = []
    for repo in repositories:
        result.append({
            "repo_name": repo.repository_name,
            "user_email": repo.user.email  # ← Lazy loading triggers query
        })
    return result
```

**Expected Query Count:** 1 (initial) + N (one per repository) = N+1 queries

**Correct Implementation:**
```python
# ✅ GOOD - Eager load user relationship
from sqlalchemy.orm import selectinload

@router.get("/users/{user_id}/repositories")
async def list_user_repositories(user_id: int, db: Session = Depends(get_db)):
    repositories = db.query(GitRepository)\
        .options(selectinload(GitRepository.user))\
        .filter_by(user_id=user_id)\
        .all()

    result = []
    for repo in repositories:
        result.append({
            "repo_name": repo.repository_name,
            "user_email": repo.user.email  # ← Already loaded, no query
        })
    return result
```

**Query Count:** 2 queries (repositories + users) = Fixed N+1

---

### Scenario 2: Multi-User Repository Listing (Medium Risk)

**Hypothetical Anti-Pattern:**
```python
# ❌ BAD - Would cause N+1 query
@router.get("/repositories")
async def list_all_repositories(db: Session = Depends(get_db)):
    repositories = db.query(GitRepository).all()

    # N+1: Each repository access triggers user query
    result = []
    for repo in repositories:
        result.append({
            "repo": repo.repository_name,
            "provider": repo.provider,
            "user": repo.user.email  # ← Lazy loading
        })
    return result
```

**Correct Implementation:**
```python
# ✅ GOOD - Eager load with selectinload
from sqlalchemy.orm import selectinload

repositories = db.query(GitRepository)\
    .options(selectinload(GitRepository.user))\
    .all()
```

---

## Index Analysis

### Current Indexes ✅

| Table | Column | Query Pattern | Status |
|-------|--------|---------------|--------|
| `users` | `id` | Primary key lookups | ✅ Optimal |
| `users` | `email` | Authentication queries | ✅ Optimal |
| `repositories` | `id` | Primary key lookups | ✅ Optimal |
| `repositories` | `user_id` | Foreign key filtering | ✅ Optimal |

### Recommended Index Addition 📋

**Composite Index for Repository Queries:**

If adding queries that filter by both `user_id` and `provider`:

```sql
CREATE INDEX idx_repositories_user_provider ON repositories(user_id, provider);
```

**Benefit:** Optimizes queries like:
```python
# Would use composite index
db.query(GitRepository).filter_by(user_id=1, provider="github").all()
```

**Priority:** LOW (only needed if such queries are added)

---

## Connection Pool Settings

**Current Configuration** (from `core/database.py`):
```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,     # ✅ Health checks enabled
    pool_size=10,           # Max persistent connections
    max_overflow=20,        # Max additional connections
)
```

**Analysis:**
- ✅ `pool_pre_ping` prevents stale connections
- ✅ `pool_size=10` is reasonable for moderate traffic
- ✅ `max_overflow=20` allows burst handling

**Recommendation:** Current settings are appropriate for the current query load. No changes needed.

---

## Eager Loading Patterns Reference

### SQLAlchemy Eager Loading Strategies

| Strategy | Use Case | Performance | Notes |
|----------|----------|-------------|-------|
| `selectinload()` | One-to-many, many-to-one | ⚡ Fast | Uses separate query with IN clause |
| `joinedload()` | One-to-one, many-to-one | ⚡ Fast | Uses JOIN (single query) |
| `subqueryload()` | One-to-many (nested) | 🐌 Slower | Uses subquery (avoid unless needed) |

### Recommended Pattern for This Codebase

**For User → Repositories (one-to-many):**
```python
from sqlalchemy.orm import selectinload

# Load user with repositories
user = db.query(User)\
    .options(selectinload(User.repositories))\
    .filter(User.id == user_id)\
    .first()

# Access repositories without additional queries
for repo in user.repositories:
    print(repo.repository_name)  # No query
```

**For Repository → User (many-to-one):**
```python
from sqlalchemy.orm import joinedload

# Load repositories with user (faster for many-to-one)
repositories = db.query(GitRepository)\
    .options(joinedload(GitRepository.user))\
    .filter(GitRepository.provider == "github")\
    .all()

# Access user without additional queries
for repo in repositories:
    print(repo.user.email)  # No query (pre-joined)
```

---

## Recommendations

### Immediate Actions ✅

1. **No urgent fixes needed** - Current codebase has no N+1 queries

### Future Prevention 📋

1. **Add documentation comment** to route templates:
   ```python
   # When adding queries with relationships, use eager loading:
   # from sqlalchemy.orm import selectinload, joinedload
   ```

2. **Consider composite index** if multi-column queries are added:
   ```sql
   CREATE INDEX idx_repositories_user_provider ON repositories(user_id, provider);
   ```

3. **Add query monitoring** in development:
   ```python
   # Log all queries in development mode
   if settings.DEBUG:
       import logging
       logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
   ```

4. **Create test case** for N+1 detection:
   ```python
   def test_no_n1_queries_on_repository_list(client, db):
       """Ensure repository list doesn't trigger N+1 queries"""
       # Assert query count is bounded
       ...
   ```

---

## Appendix: Eager Loading Quick Reference

### Import Statements
```python
from sqlalchemy.orm import selectinload, joinedload, subqueryload
```

### Usage Examples

**Load user's repositories:**
```python
user = db.query(User)\
    .options(selectinload(User.repositories))\
    .filter(User.id == user_id)\
    .first()
```

**Load repositories with user info:**
```python
repos = db.query(GitRepository)\
    .options(joinedload(GitRepository.user))\
    .all()
```

**Load nested relationships (if added in future):**
```python
# Example: User → Repositories → Commits
user = db.query(User)\
    .options(selectinload(User.repositories).selectinload(GitRepository.commits))\
    .first()
```

---

**Audit Completed:** 2026-02-25
**Status:** ✅ PASSED - No N+1 queries detected
**Next Review:** After adding new database-backed features
