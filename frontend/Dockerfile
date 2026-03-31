# ---- Stage 1: Build React SPA ----
FROM node:22-alpine AS builder

WORKDIR /app

# Copy dependency specs first for Docker layer caching
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# ---- Stage 2: Serve with Nginx ----
FROM nginx:1.27-alpine

# Remove default Nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy built SPA from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx server config
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Nginx master runs as root (required to bind port 80),
# worker processes drop to nginx user (configured in /etc/nginx/nginx.conf).
CMD ["nginx", "-g", "daemon off;"]
