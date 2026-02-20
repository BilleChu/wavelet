# OpenFinance Frontend Dockerfile
# Development build with debug support

FROM node:20-alpine

WORKDIR /app

# Install dependencies for native modules and development tools
RUN apk add --no-cache \
    libc6-compat \
    curl \
    vim \
    bash \
    procps \
    net-tools

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci --include=dev 2>/dev/null || npm install

# Copy application code
COPY . .

# Set environment variables
ENV NODE_ENV=development
ENV NEXT_TELEMETRY_DISABLED=1
ENV DEBUG=*

# Expose ports
# 3000: Next.js dev server
# 9229: Node.js debugger
# 9230: Node.js inspector
EXPOSE 3000 9229 9230

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Development entrypoint
CMD ["npm", "run", "dev"]
