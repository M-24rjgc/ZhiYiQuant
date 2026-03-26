# ZhiYiQuant Frontend Dockerfile
# Stage 1: Build
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (prefer npm)
RUN npm install --legacy-peer-deps

# Copy source code
COPY . .

# Build production version
RUN npm run build

# Stage 2: Production image (using nginx)
# Use specific version to avoid mirror registry issues
FROM nginx:1.25-alpine

# Copy build artifacts
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY deploy/nginx-docker.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
