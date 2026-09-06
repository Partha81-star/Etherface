#!/bin/sh
set -eu

echo "Deploying ContentRegistry to ${RPC_URL:-http://hardhat-node:8545}..."
cd /workspace/chain
npx hardhat run scripts/deploy.js --network localhost

echo "Seeding any authorized images present in the manifest..."
cd /workspace/backend
python -m app.seed_data

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
