# Multi-stage Dockerfile for Auto Code Web Frontend (Vite + React)
# Stage 1: Build stage with Node.js
FROM node:24-slim AS builder

# Set working directory
WORKDIR /app

# Copy package files and install dependencies first (layer caching)
COPY package*.json ./
RUN npm ci --only=production=false

# Copy source code and build (filtered by .dockerignore)
COPY src/ ./src/
COPY public/ ./public/
COPY index.html tsconfig*.json vite.config.* ./
RUN npm run build

# Stage 2: Runtime stage with nginx
FROM nginx:1.27-alpine

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create non-root user for nginx
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# Switch to non-root user
USER nginx

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
