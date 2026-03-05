# SearXNG Integration Guide

This document covers setting up and using SearXNG as a free, self-hosted alternative to Anthropic's built-in WebSearch tool ($0.01/query). SearXNG integration is **optional** - if not configured, Auto Claude continues to use Anthropic's WebSearch tool.

## What It Does

SearXNG integration enables AI agents to perform unlimited web searches at zero cost through a self-hosted metasearch engine:

- **Free Web Search**: Unlimited searches without per-query costs ($0.00 vs $0.01 per query)
- **Privacy-Respecting**: No tracking, logs, or profiling of search queries
- **Multi-Engine Aggregation**: Results from DuckDuckGo, Brave, Google, Bing, Wikipedia, and more
- **Self-Hosted**: Full control over search configuration and engine selection
- **MCP Integration**: Seamless integration with Auto Claude agents via Model Context Protocol

## When to Use SearXNG

- You're running many web searches during development and want to reduce costs
- You want privacy-respecting search without tracking or profiling
- You need to customize which search engines to use (e.g., prioritize DuckDuckGo over Google)
- You're building agents that perform bulk research or large-scale web crawling
- You want to avoid hitting Anthropic API rate limits on WebSearch

## Prerequisites

- Docker installed and running (required for SearXNG container)
- Basic familiarity with Docker command-line
- Auto Claude backend installed
- Port 8888 available on localhost (default SearXNG port)

## Security Warning

> **WARNING: Self-hosted search engines expose a web service on your machine.** SearXNG binds to `0.0.0.0` by default, making it accessible from other devices on your network if port 8888 is not firewalled.

**Required mitigations:**

1. **Bind to localhost only** -- Modify Docker command or docker-compose.yml to expose only on 127.0.0.1:
   ```bash
   # Docker run example
   docker run -d -p 127.0.0.1:8888:8080 searxng/searxng

   # Verify port is only on localhost
   netstat -an | grep 8888   # Should show 127.0.0.1:8888, NOT 0.0.0.0:8888
   ```
2. **Firewall the port** -- Block port 8888 from external access using OS firewall rules
3. **Use in development only** -- SearXNG is not designed for production public internet exposure
4. **Set strong secret key** -- Always override `SEARXNG_SECRET_KEY` with a unique value
5. **Disable image proxy** -- Image proxy can be abused; disable if not needed:
   ```yaml
   # In searxng-settings.yml
   result_proxy:
     enabled: false
   ```

## Setup

**Step 1:** Create SearXNG settings file

Create a file named `searxng-settings.yml` in your project directory:

```yaml
# searxng-settings.yml
# Basic configuration for Auto Claude integration

server:
  # REQUIRED: Disable limiter for self-hosted use
  limiter: false
  # Bind to all interfaces (Docker will handle port binding)
  port: 8080

search:
  # CRITICAL: JSON format must be enabled for MCP bridge
  formats:
    - html
    - json

  # Recommended engines for reliable results
  engines:
    - name: duckduckgo
      disabled: false
    - name: brave
      disabled: false
    - name: wikipedia
      disabled: false
    - name: google
      disabled: true  # Google has strict rate limits
    - name: bing
      disabled: true  # Bing has strict rate limits

# Optional: Customize search behavior
ui:
  infinite_scroll: true

# Optional: Set time limits for searches
outgoing:
  request_timeout: 10.0
  max_request_timeout: 15.0
```

**Step 2:** Start SearXNG container

Navigate to your project directory:

```bash
cd /path/to/your/project
```

Start SearXNG using Docker (choose one method):

**Option A: Docker run (simplest)**

```bash
docker run -d \
  --name searxng \
  -p 127.0.0.1:8888:8080 \
  -v $(pwd)/searxng-settings.yml:/etc/searxng/settings.yml:ro \
  -e SEARXNG_SECRET_KEY="$(openssl rand -base64 32)" \
  --restart unless-stopped \
  searxng/searxng:latest
```

**Option B: Docker Compose (recommended for persistence)**

Create `docker-compose.searxng.yml`:

```yaml
version: '3.8'
services:
  searxng:
    image: searxng/searxng:latest
    container_name: searxng
    ports:
      - "127.0.0.1:8888:8080"
    volumes:
      - ./searxng-settings.yml:/etc/searxng/settings.yml:ro
    environment:
      - SEARXNG_SECRET_KEY=${SEARXNG_SECRET_KEY}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

Generate a secret key and start:

```bash
# Generate secret key
echo "SEARXNG_SECRET_KEY=$(openssl rand -base64 32)" > .env.searxng

# Start SearXNG
docker-compose -f docker-compose.searxng.yml up -d
```

**Step 3:** Verify SearXNG is running

```bash
# Test web interface (optional)
open http://localhost:8888

# Test JSON API (required for MCP)
curl "http://localhost:8888/search?q=test&format=json"

# Expected response: JSON with search results
```

**Step 4:** Enable SearXNG in Auto Claude

Navigate to the backend directory:

```bash
cd apps/backend
```

Edit `.env` and enable SearXNG:

```bash
# SearXNG Search Integration (OPTIONAL)
SEARXNG_ENABLED=true

# SearXNG instance URL (default: http://localhost:8888)
SEARXNG_URL=http://localhost:8888
```

**Step 5:** Run Auto Claude with SearXNG

```bash
cd apps/backend

# Run a build with SearXNG enabled
python run.py --spec 001

# Or test SearXNG directly
python run.py --task "Search for information about Python async patterns"
```

## How It Works

### Agent Workflow

When SearXNG is enabled, agents use these tools instead of Anthropic's WebSearch:

**1. Web Search via SearXNG**
```
Tool: mcp__searxng__web_search
Args: {"query": "Python async await best practices"}
```
The agent searches the web through SearXNG and gets results from multiple engines.

**2. Read URL Content**
```
Tool: mcp__searxng__read_url
Args: {"url": "https://example.com/article"}
```
The agent fetches and parses the full content of a specific URL.

**3. Result Aggregation**
SearXNG aggregates results from configured engines (DuckDuckGo, Brave, Wikipedia, etc.) and returns them in a unified JSON format.

### Example Agent Session

Here's an example of how an agent uses SearXNG for research:

```markdown
AGENT: Researching Python async patterns...

1. Searching web for "Python async await best practices"
   → [mcp__searxng__web_search called]
   → Found 15 results from DuckDuckGo, Brave, Wikipedia

2. Reading top result: https://docs.python.org/3/library/asyncio.html
   → [mcp__searxng__read_url called]
   → Fetched 2,345 words from documentation

3. Reading second result: https://realpython.com/async-python/
   → [mcp__searxng__read_url called]
   → Fetched 3,892 words from tutorial

4. Synthesizing information...
   → Combined insights from multiple sources
   → Generated summary with code examples

RESEARCH COMPLETE:
- Sources searched: 3 engines (DuckDuckGo, Brave, Wikipedia)
- Articles read: 2
- Total cost: $0.00 (vs $0.03 with WebSearch)
```

## Available SearXNG Tools

When SearXNG integration is enabled, agents have access to these MCP tools:

| Tool | Purpose |
|------|---------|
| `mcp__searxng__web_search` | Search the web via SearXNG metasearch engine |
| `mcp__searxng__read_url` | Fetch and parse content from a specific URL |

### Tool Parameters

**web_search**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query string |
| `engines` | list | No | Specific engines to use (default: all enabled) |
| `categories` | list | No | Search categories (general, images, videos, etc.) |
| `language` | string | No | Result language (default: en) |
| `time_range` | string | No | Time filter (day, week, month, year) |

**read_url**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Yes | URL to fetch and parse |

## Configuration Options

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SEARXNG_ENABLED` | Yes | `false` | Enable SearXNG MCP server integration |
| `SEARXNG_URL` | No | `http://localhost:8888` | Base URL for SearXNG instance |
| `SEARXNG_SECRET_KEY` | Yes* | (auto-generated) | Secret key for SearXNG instance |

*Required for SearXNG container, not for Auto Claude backend

## Troubleshooting

### Issue: SearXNG container won't start

**Symptoms:** `docker run` fails or container exits immediately

**Solutions:**

1. Check port availability:
   ```bash
   # Verify port 8888 is not in use
   lsof -i :8888  # macOS/Linux
   netstat -an | findstr :8888  # Windows

   # Use different port if needed
   docker run -d -p 127.0.0.1:9999:8080 searxng/searxng
   # Then update SEARXNG_URL=http://localhost:9999
   ```

2. Check settings.yml syntax:
   ```bash
   # Validate YAML syntax
   python -c "import yaml; yaml.safe_load(open('searxng-settings.yml'))"

   # Fix any YAML errors before starting container
   ```

3. Check Docker logs:
   ```bash
   # View container logs
   docker logs searxng

   # Follow logs in real-time
   docker logs -f searxng
   ```

### Issue: JSON API returns HTML instead of JSON

**Symptoms:** `curl` returns HTML when `format=json` is specified

**Solutions:**

1. Verify JSON format is enabled in settings.yml:
   ```yaml
   search:
     formats:
       - html
       - json  # CRITICAL: This must be present
   ```

2. Restart SearXNG after changing settings:
   ```bash
   docker restart searxng
   ```

3. Test JSON endpoint again:
   ```bash
   curl "http://localhost:8888/search?q=test&format=json"
   # Should return JSON, not HTML
   ```

### Issue: Search results are empty or limited

**Symptoms:** Web search returns few or no results

**Solutions:**

1. Check engine status:
   ```bash
   # Test specific engine
   curl "http://localhost:8888/search?q=test&format=json&engines=duckduckgo"
   ```

2. Enable more engines in settings.yml:
   ```yaml
   engines:
     - name: duckduckgo
       disabled: false
     - name: brave
       disabled: false
     - name: wikipedia
       disabled: false
   ```

3. Check for rate limiting:
   ```bash
   # SearXNG logs will show rate limit errors
   docker logs searxng | grep -i "rate"
   ```

4. Switch to more reliable engines:
   - DuckDuckGo and Brave have generous rate limits
   - Google and Bing are more restrictive; consider disabling them

### Issue: MCP bridge can't connect to SearXNG

**Symptoms:** Agent logs "SearXNG connection failed" or similar

**Solutions:**

1. Verify SearXNG is running:
   ```bash
   docker ps | grep searxng
   # Should show searxng container is running
   ```

2. Test SearXNG URL manually:
   ```bash
   # Use the same URL from .env
   curl "http://localhost:8888/search?q=test&format=json"

   # If this fails, SearXNG is not running correctly
   ```

3. Check SEARXNG_URL in .env:
   ```bash
   # Verify URL is correct
   grep SEARXNG_URL apps/backend/.env
   # Should show: SEARXNG_URL=http://localhost:8888
   ```

4. Verify MCP bridge is installed:
   ```bash
   # Test MCP bridge directly
   npx -y mcp-searxng --help
   # Should show help message
   ```

### Issue: High memory usage by SearXNG container

**Symptoms:** Docker container using >1GB RAM

**Solutions:**

1. Limit container memory:
   ```bash
   docker run -d \
     --name searxng \
     --memory="512m" \
     --memory-swap="1g" \
     -p 127.0.0.1:8888:8080 \
     searxng/searxng
   ```

2. Reduce result caching:
   ```yaml
   # In searxng-settings.yml
   search:
     cache:
       enabled: false  # Disable caching to reduce memory
   ```

3. Disable unused engines:
   ```yaml
   # Fewer engines = less memory
   engines:
     - name: duckduckgo
       disabled: false
     # Disable other engines you don't need
   ```

## Best Practices

### Engine Selection

- **Prefer DuckDuckGo and Brave** - More generous rate limits, no API keys needed
- **Disable Google and Bing** - Strict rate limits, may block automated queries
- **Add Wikipedia** - Excellent for definitions and background information
- **Avoid niche engines** - Unless you have specific needs (e.g., Stack Overflow for code)

### Performance Optimization

- **Use JSON format only** - Disable HTML if you only need MCP integration
- **Limit time range** - Use `time_range: "week"` for faster, more relevant results
- **Cache locally** - Auto Claude's Graphiti memory caches search results automatically
- **Parallel searches** - Agents can run multiple searches in parallel when needed

### Security Hardening

- **Bind to localhost** - Always use `127.0.0.1:8888` not `0.0.0.0:8888`
- **Use strong secret key** - Generate with `openssl rand -base64 32`
- **Disable image proxy** - Set `result_proxy.enabled: false` unless needed
- **Limit container resources** - Use `--memory` and `--cpus` flags
- **Update regularly** - Pull latest image: `docker pull searxng/searxng:latest`

### Cost Management

- **Compare costs**:
  - Anthropic WebSearch: $0.01 per query
  - SearXNG: $0.00 per query (only your server's electricity)
- **Break-even point**: If you do >100 searches/day, SearXNG pays for itself quickly
- **Use both strategically**: Keep WebSearch available as fallback for critical queries

### Monitoring and Maintenance

- **Health checks** - Use Docker healthcheck to monitor container status
- **Log rotation** - Configure log driver to prevent disk space issues:
  ```bash
  docker run -d --log-driver json-file --log-opt max-size=10m searxng/searxng
  ```
- **Regular updates** - Update SearXNG monthly for bug fixes and new features
- **Monitor usage** - Check `docker stats searxng` for resource usage

## Docker Compose Examples

### Minimal Setup

```yaml
version: '3.8'
services:
  searxng:
    image: searxng/searxng:latest
    container_name: searxng
    ports:
      - "127.0.0.1:8888:8080"
    restart: unless-stopped
```

### Production-Ready Setup

```yaml
version: '3.8'
services:
  searxng:
    image: searxng/searxng:latest
    container_name: searxng
    ports:
      - "127.0.0.1:8888:8080"
    volumes:
      - ./searxng-settings.yml:/etc/searxng/settings.yml:ro
    environment:
      - SEARXNG_SECRET_KEY=${SEARXNG_SECRET_KEY}
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    logging:
      driver: json-file
      options:
        max-size: 10m
        max-file: '3'
```

## Disable SearXNG Integration

To disable SearXNG integration after enabling:

```bash
# Remove or comment out in apps/backend/.env
# SEARXNG_ENABLED=true

# Stop SearXNG container (optional)
docker stop searxng
docker rm searxng
```

Auto Claude will automatically fall back to Anthropic's WebSearch tool.

## Platform-Specific Notes

### Windows

- Use PowerShell for secret key generation:
  ```powershell
  -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
  ```
- Path syntax for Docker volumes:
  ```bash
  # Windows Command Prompt
  docker run -d -p 127.0.0.1:8888:8080 -v %cd%\searxng-settings.yml:/etc/searxng/settings.yml:ro searxng/searxng

  # PowerShell
  docker run -d -p 127.0.0.1:8888:8080 -v "${PWD}/searxng-settings.yml:/etc/searxng/settings.yml:ro" searxng/searxng
  ```
- Firewall may prompt for port 8888 - block it for external networks

### macOS

- Use `openssl` for secret key generation (pre-installed on macOS)
- Docker Desktop for Mac required
- Path syntax uses `$(pwd)`:
  ```bash
  docker run -d -p 127.0.0.1:8888:8080 -v $(pwd)/searxng-settings.yml:/etc/searxng/settings.yml:ro searxng/searxng
  ```

### Linux

- Install Docker via package manager:
  ```bash
  sudo apt install docker.io  # Ubuntu/Debian
  sudo dnf install docker     # Fedora
  ```
- Add user to docker group to avoid sudo:
  ```bash
  sudo usermod -aG docker $USER
  ```
- Use systemd for auto-start:
  ```bash
  sudo systemctl enable docker
  sudo systemctl start docker
  ```

## Secret & Environment Variable Safety

- **Never commit `.env` files** to source control -- `.env` is gitignored by default
- **Never commit `searxng-settings.yml` with real secret keys** - Use placeholder in version control
- **Use separate .env files** for development and production
- **Rotate secret keys** periodically (every 60-90 days recommended)
- **Audit container access** -- review who has access to Docker daemon
- **Scan for secrets** before committing:
  ```bash
  # Install git-secrets
  git secrets --install
  git secrets --register-azure
  git secrets --scan
  ```

## See Also

- [Electron MCP Integration Guide](./INTEGRATION-ELECTRON-MCP.md) - E2E testing for Electron apps
- [Graphiti Memory Integration Guide](./INTEGRATION-GRAPHITI.md) - Knowledge graph for AI agents
- [Linear Integration Guide](./INTEGRATION-LINEAR.md) - Issue tracking integration
- [CLI Usage Guide](./CLI-USAGE.md) - Terminal-only Auto Claude usage

## External Resources

- [SearXNG Documentation](https://searxng.github.io/searxng/)
- [SearXNG GitHub](https://github.com/searxng/searxng)
- [mcp-searxng npm package](https://www.npmjs.com/package/mcp-searxng)
- [Docker Installation Guide](https://docs.docker.com/get-docker/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
