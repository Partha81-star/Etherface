.PHONY: up down seed deploy-contract test test-chain test-backend build-frontend

up:
	docker compose up --build

down:
	docker compose down

seed:
	docker compose exec backend python -m app.seed_data

deploy-contract:
	cd chain && npm run deploy

test: test-chain test-backend build-frontend

test-chain:
	cd chain && npm test

test-backend:
	cd backend && pytest -q

build-frontend:
	cd frontend && npm run build
