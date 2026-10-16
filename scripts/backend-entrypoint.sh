#!/bin/sh
set -e

# ---------------------------------------------------------------------------
# Ensure the SQLite database directory exists (handles Railway volume or
# any custom DATABASE_URL path like sqlite+aiosqlite:////data/face_verify.db)
# ---------------------------------------------------------------------------
DB_URL="${DATABASE_URL:-sqlite+aiosqlite:///./face_verify.db}"
# Extract the file path: strip the driver prefix up to the 3rd slash
DB_FILE=$(echo "$DB_URL" | sed 's|.*sqlite[^:]*:///||')
if [ -n "$DB_FILE" ] && [ "$DB_FILE" != "$DB_URL" ]; then
  DB_DIR=$(dirname "$DB_FILE")
  if [ "$DB_DIR" != "." ] && [ "$DB_DIR" != "" ]; then
    echo "Ensuring database directory exists: $DB_DIR"
    mkdir -p "$DB_DIR"
  fi
fi

# ---------------------------------------------------------------------------
# Chain deployment (optional) — skipped gracefully if RPC is not reachable.
# Set SKIP_CHAIN_DEPLOY=1 to bypass entirely (e.g. on Railway without a
# Hardhat node service).
# ---------------------------------------------------------------------------
RPC="${RPC_URL:-http://hardhat-node:8545}"

if [ "${SKIP_CHAIN_DEPLOY:-0}" = "1" ]; then
  echo "SKIP_CHAIN_DEPLOY=1 — skipping chain deployment."
else
  echo "Checking RPC connectivity at ${RPC}..."
  # Quick TCP reachability check (node one-liner, no extra deps needed)
  if node -e "
    const url = new URL('${RPC}');
    const net = require('net');
    const s = net.createConnection({host: url.hostname, port: url.port || 8545}, () => { process.exit(0); });
    s.on('error', () => process.exit(1));
    setTimeout(() => process.exit(1), 3000);
  " 2>/dev/null; then
    echo "RPC reachable — deploying ContentRegistry..."
    cd /workspace/chain
    npx hardhat run scripts/deploy.js --network localhost
    cd /workspace/backend
  else
    echo "WARNING: RPC at ${RPC} is not reachable — skipping chain deployment."
    echo "Blockchain features (verify/register) will be unavailable until an RPC is configured."
    cd /workspace/backend
  fi
fi

echo "Seeding any authorized images present in the manifest..."
cd /workspace/backend
python -m app.seed_data

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
