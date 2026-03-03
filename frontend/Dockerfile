# Stage 1 — build
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# API URL is relative so nginx can proxy — override at build time if needed
ARG VITE_PILOTARR_API_URL=/api
ENV VITE_PILOTARR_API_URL=$VITE_PILOTARR_API_URL

RUN npm run build

# Stage 2 — serve
FROM nginx:alpine

COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
