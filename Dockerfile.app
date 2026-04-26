# ── Stage 1: Build ──
FROM node:20-alpine AS builder

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /src

# 先拷贝依赖文件，利用缓存
COPY pnpm-lock.yaml pnpm-workspace.yaml ./
COPY app/package.json app/
COPY admin/package.json admin/
COPY packages/shared/package.json packages/shared/

RUN pnpm install --frozen-lockfile

# 拷贝源码
COPY packages/shared/ packages/shared/
COPY app/ app/

# 构建 app（学生端）
RUN cd app && pnpm build

# ── Stage 2: Serve ──
FROM nginx:alpine

COPY --from=builder /src/app/dist /usr/share/nginx/html
COPY deploy/nginx-app.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
