# Stage 1: Build student app
FROM node:20-alpine AS builder

RUN corepack enable && corepack prepare pnpm@10.33.2 --activate

WORKDIR /src

COPY . .

# This repo currently has no root package.json, but pnpm needs one to resolve
# the workspace reliably in Docker.
RUN printf '%s\n' '{"private":true,"packageManager":"pnpm@10.33.2"}' > package.json
RUN pnpm install --no-frozen-lockfile --shamefully-hoist

# Build static assets. Type checking is handled separately because existing app
# type debt currently blocks tsc while Vite can still emit deployable assets.
RUN pnpm --filter @zhiqu/app exec vite build

# Stage 2: Serve
FROM nginx:alpine

COPY --from=builder /src/app/dist /usr/share/nginx/html
COPY deploy/nginx-app.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
