FROM node:22-slim AS build

WORKDIR /srv/web
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npm run build

FROM node:22-slim AS runtime
WORKDIR /srv/web
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system druk && adduser --system --ingroup druk druk

COPY --from=build /srv/web/package.json /srv/web/package-lock.json ./
COPY --from=build /srv/web/node_modules ./node_modules
COPY --from=build /srv/web/.next ./.next
COPY --from=build /srv/web/public ./public
COPY --from=build /srv/web/next.config.ts ./

USER druk
EXPOSE 3000
CMD ["npm", "run", "start"]
