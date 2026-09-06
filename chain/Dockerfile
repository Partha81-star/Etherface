FROM node:22.13-bookworm-slim

WORKDIR /workspace/chain
COPY package.json package-lock.json ./
RUN npm ci
COPY hardhat.config.js ./
COPY contracts ./contracts
COPY scripts ./scripts
COPY test ./test
RUN npm run compile

EXPOSE 8545
CMD ["npm", "run", "node"]
