# EtherFace Identity Access

EtherFace is a local-first face authentication demo with two separate portals:

- **Admin portal:** sign in, register members, capture one consented face sample,
  activate or deactivate access, and review authentication activity.
- **Member portal:** enter a member ID, take a fresh face photo, and receive a
  short-lived authenticated session when the face matches that member's template.

Face matching is one-to-one: EtherFace looks up the supplied member ID and compares
the capture only with that member. Enrollment photos and login captures are processed
in memory and discarded. SQLite stores the numerical face template, member record,
sessions, and minimal audit history.

> This is a local demonstration, not production biometric security. A still-image
> comparison has no liveness detection and can be spoofed with a photograph. Add
> liveness, MFA, rate limiting at the edge, encryption, and formal biometric-data
> governance before using this design for real access control.

## Run with Docker

Prerequisite: Docker Desktop with Compose v2.

```powershell
cd 'C:\Users\parth\Desktop\EtherFace'
docker compose up --build -d
docker compose ps
```

Open:

- Portal chooser: http://localhost:5173
- Member login: http://localhost:5173/login
- Admin portal: http://localhost:5173/admin
- API documentation: http://localhost:8000/docs
- API health: http://localhost:8000/health
- Local Hardhat RPC: http://localhost:8545

Default local admin credentials:

```text
Email:    admin@faceverify.local
Password: admin123
```

The default is only for local checking. Generate a replacement PBKDF2 password hash:

```powershell
docker compose run --rm --no-deps --entrypoint python backend -m app.auth_service
```

Put the output in a root `.env` file, keeping the value in single quotes because it
contains dollar signs:

```dotenv
ADMIN_EMAIL=your-admin@example.com
ADMIN_NAME=Your Administrator
ADMIN_PASSWORD_HASH='pbkdf2_sha256$...'
```

Restart the backend after changing credentials:

```powershell
docker compose up --build -d backend frontend
```

Useful lifecycle commands:

```powershell
docker compose logs -f
docker compose restart
docker compose down
```

`docker compose down` preserves the SQLite volume. Use `docker compose down -v`
only when you intentionally want to delete every member, session, and audit record.

## Application flow

### Register a member

1. Open `/admin` and sign in.
2. Select **Register member**.
3. Enter a unique member ID, name, email, and optional department.
4. Use the camera or upload one clear front-facing face photo.
5. Confirm that the member consented to biometric processing.
6. Submit. The photo is discarded after the numerical template is stored.

The member becomes active immediately. Duplicate IDs, emails, and already-enrolled
faces are rejected. Images with zero or multiple detected faces are also rejected.

### Authenticate a member

1. Open `/login`.
2. Enter the member ID assigned during enrollment.
3. Capture a fresh image or use the upload fallback.
4. Select **Authenticate and sign in**.
5. A successful match opens the member account screen and creates a one-hour session.

Failures return a generic response and do not reveal another member's identity.
Deactivating a member immediately revokes their active sessions.

## Run manually without Docker

Use Python 3.11 and Node.js 22.13 or newer. Open three PowerShell terminals.

### Terminal 1: local blockchain

```powershell
cd 'C:\Users\parth\Desktop\EtherFace\chain'
npm.cmd install
npm.cmd run node
```

### Terminal 2: deploy contract and start API

Wait until Terminal 1 reports that Hardhat is listening, then run:

```powershell
cd 'C:\Users\parth\Desktop\EtherFace\chain'
npm.cmd run deploy

cd '..\backend'
py -3.11 -m venv .venv311
.\.venv311\Scripts\python.exe -m pip install -r requirements-dlib.txt
.\.venv311\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

If dlib cannot build, use the MediaPipe demonstration fallback:

```powershell
.\.venv311\Scripts\python.exe -m pip install -r requirements.txt
$env:FACE_BACKEND = 'mediapipe'
.\.venv311\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### Terminal 3: frontend

```powershell
cd 'C:\Users\parth\Desktop\EtherFace\frontend'
npm.cmd install
npm.cmd run dev
```

## Tests

```powershell
cd 'C:\Users\parth\Desktop\EtherFace\backend'
.\.venv\Scripts\python.exe -m pytest -q

cd '..\chain'
npm.cmd test

cd '..\frontend'
npm.cmd run build
```

The backend suite uses an isolated ignored test database. The optional live-chain
test remains behind the `RUN_CHAIN_TESTS=1` environment variable.

## Privacy and security boundaries

- Only members explicitly enrolled by an authenticated administrator are matched.
- Login is member-ID plus face, not directory-wide face identification.
- Login captures and enrollment photos are not retained as image files.
- Face templates, access tokens, and match distances are never returned by member APIs.
- Admin and member sessions are random opaque tokens stored as SHA-256 digests.
- Admin passwords use PBKDF2-HMAC-SHA256 hashes; plaintext passwords are not stored.
- Services bind to `127.0.0.1`, including Hardhat's unlocked development accounts.
- The MediaPipe fallback is demo-grade and should not be treated as a production
  recognition model.
- No biometric image, template, member identity, or login event is written on-chain.

The legacy consented-post and blockchain integrity endpoints remain available for
the original provenance demo, but blockchain mutation now requires an admin session.
