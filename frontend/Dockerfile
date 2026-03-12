# Stage 1: Install dependencies
FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json* ./

# frozen-lockfile equivalent for npm
RUN npm ci && npm cache clean --force


# Stage 2: Build production bundle
FROM node:20-alpine AS builder

WORKDIR /app

# Bring in node_modules from deps stage (layer-cached)
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build-time env vars (overridable with --build-arg)
ARG REACT_APP_API_URL=http://localhost:8000
ARG REACT_APP_API_BASE_URL=http://localhost:8000
ARG GENERATE_SOURCEMAP=false
ARG INLINE_RUNTIME_CHUNK=false

ENV REACT_APP_API_URL=${REACT_APP_API_URL} \
    REACT_APP_API_BASE_URL=${REACT_APP_API_BASE_URL} \
    GENERATE_SOURCEMAP=${GENERATE_SOURCEMAP} \
    INLINE_RUNTIME_CHUNK=${INLINE_RUNTIME_CHUNK} \
    NODE_OPTIONS="--max-old-space-size=4096"

RUN npm run build


# Stage 3: Serve with nginx
FROM nginx:1.27-alpine AS runtime

LABEL maintainer="Travello Team" \
      description="Travello React SPA served by nginx" \
      org.opencontainers.image.source="https://github.com/travello/travello"

# nginx configuration (SPA routing + gzip + security)
RUN rm /etc/nginx/conf.d/default.conf && \
    cat > /etc/nginx/conf.d/travello.conf <<'NGINX'
server {
    listen       80;
    server_name  _;

    root   /usr/share/nginx/html;
    index  index.html;

    # ─── Gzip compression ───────────────────────────────
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 256;
    gzip_types
        text/plain text/css text/xml text/javascript
        application/json application/javascript application/xml
        application/rss+xml application/atom+xml
        image/svg+xml font/woff2;

    # ─── Cache hashed static assets (1 year) ────────────
    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # ─── SPA — serve index.html for all client routes ───
    location / {
        try_files $uri $uri/ /index.html;
    }

    # ─── Security headers ───────────────────────────────
    add_header X-Frame-Options           "SAMEORIGIN"                   always;
    add_header X-Content-Type-Options    "nosniff"                      always;
    add_header Referrer-Policy           "strict-origin-when-cross-origin" always;
    add_header X-XSS-Protection          "1; mode=block"                always;
    add_header Permissions-Policy        "camera=(), microphone=(), geolocation=(self)" always;

    # ─── Disable server version leak ────────────────────
    server_tokens off;
}
NGINX

# Copy the production build from the builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Run nginx as non-root (security best-practice)
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
