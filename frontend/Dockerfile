FROM node:22-alpine

WORKDIR /app

# 環境変数設定
ENV NODE_ENV=development
ENV WATCHPACK_POLLING=true

COPY package*.json ./
RUN npm install

COPY . .

# 開発モードで実行
CMD ["npm", "run", "dev"] 
