FROM node:22-slim

ENV NODE_ENV=development

WORKDIR /app

COPY package.json package-lock.json .npmrc ./
RUN npm ci

COPY app app
COPY build build
COPY public public
COPY scripts scripts
COPY worker worker
COPY .openai .openai
COPY eslint.config.mjs next.config.ts postcss.config.mjs tsconfig.json ./
COPY vite.config.ts drizzle.config.ts ./

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
