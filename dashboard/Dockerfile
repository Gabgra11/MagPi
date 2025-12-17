FROM node:18-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci

COPY . .

RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci --only=production

COPY --from=builder /app/dist ./dist
COPY server ./server

EXPOSE 3000

ENV NODE_ENV=production
ENV DASHBOARD_PORT=3000

CMD ["node", "server/index.js"]
