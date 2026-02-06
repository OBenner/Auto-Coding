# Deployment Guide - Auto Code Web Frontend

This guide covers deploying the Auto Code Web Frontend (React/Vite application) to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Building for Production](#building-for-production)
- [Environment Configuration](#environment-configuration)
- [Deployment Options](#deployment-options)
  - [Static Hosting (Vercel, Netlify)](#static-hosting-vercel-netlify)
  - [Cloud Storage + CDN](#cloud-storage--cdn)
  - [Docker + Nginx](#docker--nginx)
  - [Traditional Web Server](#traditional-web-server)
- [Backend Integration](#backend-integration)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Node.js**: >= 24.0.0
- **npm**: >= 10.0.0
- **Backend API**: Deployed and accessible (see `apps/web-backend/DEPLOYMENT.md`)

### Verify Installation

```bash
node --version  # Should be >= v24.0.0
npm --version   # Should be >= 10.0.0
```

---

## Building for Production

### 1. Clone Repository

```bash
git clone https://github.com/OBenner/Auto-Coding.git
cd Auto-Claude/apps/web-frontend
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Configure Environment

Create `.env.production`:

```env
# Backend API URL (IMPORTANT: Use your production backend URL)
VITE_API_URL=https://api.your-domain.com

# WebSocket URL (IMPORTANT: Use wss:// for HTTPS)
VITE_WS_URL=wss://api.your-domain.com

# Enable production mode
NODE_ENV=production

# Disable debug logging
VITE_DEBUG=false

# Enable WebSocket
VITE_ENABLE_WEBSOCKET=true

# Optional: Sentry error tracking
# VITE_SENTRY_DSN=https://your-dsn@sentry.io/project-id
# VITE_SENTRY_TRACES_SAMPLE_RATE=0.1
```

**Important**:
- Use `https://` for `VITE_API_URL` in production
- Use `wss://` (secure WebSocket) for `VITE_WS_URL` in production
- Never commit `.env.production` to version control if it contains secrets

### 4. Build the Application

```bash
npm run build
```

**Output**: The build artifacts will be in the `dist/` directory.

**Verify build**:

```bash
# Check dist directory
ls -lh dist/

# Preview production build locally
npm run preview
```

The build process:
- ✅ Minifies JavaScript and CSS
- ✅ Optimizes images and assets
- ✅ Generates source maps (for debugging)
- ✅ Creates index.html with asset hashes
- ✅ Bundles dependencies efficiently

**Expected output structure**:

```
dist/
├── index.html           # Entry point
├── assets/
│   ├── index-[hash].js  # Main bundle
│   ├── index-[hash].css # Styles
│   └── ...              # Other chunks
├── favicon.ico
└── ...
```

---

## Environment Configuration

### Environment Variables

The frontend uses Vite environment variables (prefixed with `VITE_`):

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API base URL | `https://api.example.com` |
| `VITE_WS_URL` | WebSocket server URL | `wss://api.example.com` |
| `VITE_DEBUG` | Enable debug logging | `false` (production) |
| `VITE_ENABLE_WEBSOCKET` | Enable real-time updates | `true` |
| `VITE_SENTRY_DSN` | Sentry error tracking | (optional) |
| `VITE_SENTRY_TRACES_SAMPLE_RATE` | Sentry sample rate | `0.1` |

### Multiple Environments

Create environment-specific files:

```bash
.env                  # Default (loaded in all cases)
.env.local           # Local overrides (gitignored)
.env.production      # Production environment
.env.staging         # Staging environment
```

Build for specific environment:

```bash
# Production build (uses .env.production)
npm run build

# Staging build (create custom script in package.json)
npm run build:staging
```

---

## Deployment Options

### Static Hosting (Vercel, Netlify)

#### Vercel

**Option 1: Vercel CLI**

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
vercel --prod

# Follow prompts to configure
```

**Option 2: GitHub Integration**

1. Push code to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Click "Import Project"
4. Select your repository
5. Configure build settings:
   - **Framework**: Vite
   - **Root Directory**: `apps/web-frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
6. Add environment variables (see Environment Configuration)
7. Deploy!

**Environment Variables in Vercel**:
- Go to Project Settings → Environment Variables
- Add `VITE_API_URL`, `VITE_WS_URL`, etc.
- Redeploy for changes to take effect

#### Netlify

**Option 1: Netlify CLI**

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login
netlify login

# Deploy
netlify deploy --prod --dir=dist
```

**Option 2: netlify.toml Configuration**

Create `netlify.toml` in project root:

```toml
[build]
  command = "cd apps/web-frontend && npm install && npm run build"
  publish = "apps/web-frontend/dist"

[build.environment]
  NODE_VERSION = "24.0.0"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-Content-Type-Options = "nosniff"
    X-XSS-Protection = "1; mode=block"
    Referrer-Policy = "strict-origin-when-cross-origin"

[[headers]]
  for = "/assets/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
```

Push to GitHub and connect to Netlify.

**Environment Variables in Netlify**:
- Go to Site Settings → Build & Deploy → Environment
- Add `VITE_API_URL`, `VITE_WS_URL`, etc.

---

### Cloud Storage + CDN

#### AWS (S3 + CloudFront)

**1. Build the application**:

```bash
npm run build
```

**2. Create S3 bucket**:

```bash
aws s3 mb s3://auto-claude-web-frontend

# Enable static website hosting
aws s3 website s3://auto-claude-web-frontend \
  --index-document index.html \
  --error-document index.html
```

**3. Upload build to S3**:

```bash
aws s3 sync dist/ s3://auto-claude-web-frontend \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "index.html"

# Upload index.html separately (no cache)
aws s3 cp dist/index.html s3://auto-claude-web-frontend/index.html \
  --cache-control "no-cache, no-store, must-revalidate"
```

**4. Create CloudFront distribution**:

```bash
# Via AWS Console:
# - Origin: S3 bucket
# - Viewer Protocol Policy: Redirect HTTP to HTTPS
# - Compress Objects: Yes
# - Custom Error Response: 404 → /index.html (200)
```

**5. Set up custom domain** (optional):

- Request SSL certificate in ACM
- Add CNAME record in DNS
- Update CloudFront distribution with custom domain

#### Google Cloud (Cloud Storage + Cloud CDN)

**1. Build the application**:

```bash
npm run build
```

**2. Create GCS bucket**:

```bash
gsutil mb gs://auto-claude-web-frontend
gsutil web set -m index.html -e index.html gs://auto-claude-web-frontend
```

**3. Upload build**:

```bash
gsutil -m rsync -r -d dist/ gs://auto-claude-web-frontend

# Set cache headers
gsutil -m setmeta -h "Cache-Control:public, max-age=31536000" \
  "gs://auto-claude-web-frontend/assets/**"
```

**4. Make bucket public**:

```bash
gsutil iam ch allUsers:objectViewer gs://auto-claude-web-frontend
```

**5. Set up Cloud CDN**:

- Create load balancer
- Add backend bucket
- Enable Cloud CDN
- Configure custom domain and SSL

#### Azure (Blob Storage + Azure CDN)

**1. Build the application**:

```bash
npm run build
```

**2. Create storage account and enable static website**:

```bash
az storage account create \
  --name autoclaudeweb \
  --resource-group auto-claude-rg \
  --location eastus \
  --sku Standard_LRS

az storage blob service-properties update \
  --account-name autoclaudeweb \
  --static-website \
  --index-document index.html \
  --404-document index.html
```

**3. Upload build**:

```bash
az storage blob upload-batch \
  --account-name autoclaudeweb \
  --source dist/ \
  --destination '$web'
```

**4. Set up Azure CDN** via Azure Portal.

---

### Docker + Nginx

**1. Create Dockerfile**

Create `Dockerfile` in `apps/web-frontend/`:

```dockerfile
# Stage 1: Build
FROM node:24-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Build application
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

**2. Create nginx.conf**

Create `nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Cache static assets
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA routing - serve index.html for all routes
    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

**3. Build and run Docker container**

```bash
# Build image
docker build -t auto-claude-web-frontend .

# Run container
docker run -d \
  --name auto-claude-frontend \
  -p 80:80 \
  --restart unless-stopped \
  auto-claude-web-frontend

# View logs
docker logs -f auto-claude-frontend
```

**4. docker-compose.yml** (optional)

```yaml
version: '3.8'

services:
  frontend:
    build: .
    container_name: auto-claude-frontend
    restart: unless-stopped
    ports:
      - "80:80"
    networks:
      - auto-claude-network
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

networks:
  auto-claude-network:
    external: true
```

---

### Traditional Web Server

#### Apache

**1. Build the application**:

```bash
npm run build
```

**2. Copy to web root**:

```bash
sudo cp -r dist/* /var/www/html/auto-claude/
```

**3. Configure Apache**

Create `/etc/apache2/sites-available/auto-claude.conf`:

```apache
<VirtualHost *:80>
    ServerName web.your-domain.com
    DocumentRoot /var/www/html/auto-claude

    # Redirect to HTTPS
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^(.*)$ https://%{HTTP_HOST}$1 [R=301,L]
</VirtualHost>

<VirtualHost *:443>
    ServerName web.your-domain.com
    DocumentRoot /var/www/html/auto-claude

    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/web.your-domain.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/web.your-domain.com/privkey.pem

    # Security headers
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-XSS-Protection "1; mode=block"

    # Compression
    <IfModule mod_deflate.c>
        AddOutputFilterByType DEFLATE text/html text/plain text/xml text/css text/javascript application/javascript application/json
    </IfModule>

    # Cache static assets
    <Directory /var/www/html/auto-claude/assets>
        Header set Cache-Control "public, max-age=31536000, immutable"
    </Directory>

    # SPA routing
    <Directory /var/www/html/auto-claude>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted

        # Rewrite rules for SPA
        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\.html$ - [L]
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /index.html [L]
    </Directory>
</VirtualHost>
```

**4. Enable site**:

```bash
sudo a2enmod rewrite ssl headers deflate
sudo a2ensite auto-claude
sudo systemctl reload apache2
```

#### Nginx (standalone)

See nginx.conf in Docker section. Deploy directly:

```bash
# Copy build
sudo cp -r dist/* /var/www/auto-claude/

# Copy nginx config
sudo cp nginx.conf /etc/nginx/sites-available/auto-claude

# Enable site
sudo ln -s /etc/nginx/sites-available/auto-claude /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Backend Integration

### API URL Configuration

**Development**:
```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

**Production**:
```env
VITE_API_URL=https://api.your-domain.com
VITE_WS_URL=wss://api.your-domain.com
```

### CORS Configuration

**Ensure backend allows frontend origin**:

In backend `.env`:
```env
CORS_ORIGINS=https://web.your-domain.com
```

### WebSocket Connection

**Important**:
- Use `wss://` (secure WebSocket) in production
- Ensure reverse proxy supports WebSocket upgrades
- Configure WebSocket timeouts appropriately

**Test WebSocket in production**:

```javascript
// Browser console
const ws = new WebSocket('wss://api.your-domain.com/ws/agent-events');
ws.onopen = () => console.log('Connected');
ws.onmessage = (e) => console.log('Message:', e.data);
ws.onerror = (e) => console.error('Error:', e);
```

---

## Performance Optimization

### 1. Build Optimization

**Already enabled in Vite**:
- ✅ Code splitting
- ✅ Tree shaking
- ✅ Minification
- ✅ Asset optimization

**Manual optimizations**:

```typescript
// Lazy load routes
const TaskList = lazy(() => import('./pages/TaskList'));
const TaskDetail = lazy(() => import('./pages/TaskDetail'));

// Use Suspense
<Suspense fallback={<Loading />}>
  <TaskList />
</Suspense>
```

### 2. CDN Configuration

**Use a CDN** for:
- Static assets (JS, CSS, images)
- Reduced latency
- Better caching

**Popular CDNs**:
- CloudFlare
- Fastly
- Akamai
- AWS CloudFront

### 3. Caching Strategy

**index.html**: No cache (always fresh)
```nginx
Cache-Control: no-cache, no-store, must-revalidate
```

**Static assets**: Long-term cache (versioned with hashes)
```nginx
Cache-Control: public, max-age=31536000, immutable
```

### 4. Compression

**Enable gzip/brotli** in web server:

```nginx
# Gzip
gzip on;
gzip_types text/plain text/css application/javascript application/json;

# Brotli (if available)
brotli on;
brotli_types text/plain text/css application/javascript application/json;
```

### 5. Image Optimization

**Already optimized** by Vite during build.

**Additional optimization**:
- Use WebP format for images
- Implement lazy loading for images
- Use responsive images (`srcset`)

### 6. Monitoring Performance

**Web Vitals**:
- LCP (Largest Contentful Paint): < 2.5s
- FID (First Input Delay): < 100ms
- CLS (Cumulative Layout Shift): < 0.1

**Tools**:
- Chrome DevTools Lighthouse
- PageSpeed Insights
- WebPageTest

**Add performance monitoring**:

```typescript
// src/lib/performance.ts
import { onCLS, onFID, onLCP } from 'web-vitals';

onCLS(console.log);
onFID(console.log);
onLCP(console.log);
```

---

## Troubleshooting

### Build Errors

**Issue**: `npm run build` fails

**Solutions**:
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Update Node.js (must be >= 24.0.0)
nvm install 24
nvm use 24

# Check for TypeScript errors
npm run typecheck
```

### Blank Page in Production

**Issue**: Application loads but shows blank page

**Debug**:
1. **Check browser console** for errors
2. **Verify API URL** in `.env.production`
3. **Check network tab** for failed requests
4. **Verify CORS** configuration on backend

**Common causes**:
- Incorrect `VITE_API_URL`
- CORS not configured
- Assets not loading (check paths)

### API Connection Failures

**Issue**: Frontend can't connect to backend API

**Check**:
1. Backend is running and accessible
2. `VITE_API_URL` is correct
3. CORS is configured on backend
4. Firewall allows traffic
5. SSL certificate is valid (if using HTTPS)

**Test API manually**:
```bash
curl https://api.your-domain.com/health
```

### WebSocket Not Connecting

**Issue**: Real-time updates not working

**Debug**:
1. **Check WebSocket URL** (`VITE_WS_URL`)
2. **Use `wss://`** (secure) in production
3. **Check reverse proxy** WebSocket support
4. **Verify firewall** allows WebSocket connections

**Test WebSocket**:
```bash
npm install -g wscat
wscat -c wss://api.your-domain.com/ws/agent-events
```

### 404 Errors on Refresh

**Issue**: SPA routes return 404 when refreshing

**Solution**: Configure server to serve `index.html` for all routes

**Nginx**:
```nginx
try_files $uri $uri/ /index.html;
```

**Apache**:
```apache
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.html [L]
```

**Netlify**: Add `_redirects` file:
```
/*    /index.html   200
```

**Vercel**: Add `vercel.json`:
```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

### Slow Initial Load

**Solutions**:
1. **Enable compression** (gzip/brotli)
2. **Use CDN** for assets
3. **Implement code splitting**
4. **Lazy load routes**
5. **Optimize images**
6. **Enable HTTP/2**

---

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/deploy-frontend.yml`:

```yaml
name: Deploy Frontend

on:
  push:
    branches: [main]
    paths:
      - 'apps/web-frontend/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '24'

      - name: Install dependencies
        working-directory: apps/web-frontend
        run: npm ci

      - name: Run tests
        working-directory: apps/web-frontend
        run: npm test

      - name: Build
        working-directory: apps/web-frontend
        env:
          VITE_API_URL: ${{ secrets.VITE_API_URL }}
          VITE_WS_URL: ${{ secrets.VITE_WS_URL }}
        run: npm run build

      - name: Deploy to S3
        uses: jakejarvis/s3-sync-action@master
        with:
          args: --delete
        env:
          AWS_S3_BUCKET: ${{ secrets.AWS_S3_BUCKET }}
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          SOURCE_DIR: apps/web-frontend/dist
```

---

## Support

For deployment issues:

- **GitHub Issues**: https://github.com/OBenner/Auto-Coding/issues
- **Documentation**: See main repository README
- **Community**: Join discussions on GitHub

---

**Previous Step**: Deploy the backend - see [Backend DEPLOYMENT.md](../web-backend/DEPLOYMENT.md)
