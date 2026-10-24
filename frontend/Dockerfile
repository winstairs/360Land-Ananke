FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# Certificati radice aggiuntivi della macchina (contesto "certs", vedi certs/README.md)
RUN --mount=from=certs,target=/certs \
    cat /certs/*.crt > /tmp/extra-ca.pem 2>/dev/null; \
    if [ -s /tmp/extra-ca.pem ]; then export NODE_EXTRA_CA_CERTS=/tmp/extra-ca.pem; fi; \
    npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:stable-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
