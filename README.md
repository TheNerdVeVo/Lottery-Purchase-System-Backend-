# Lottery Purchase System (LPS) — Integrated

CS3365 Team 9, Phase 2.

The system is split into two cooperating processes:

- **Django REST API** (`SoftwareEngineering_Project2/` + `LPS/`) — owns the SQLite database and all business logic. Exposes JSON endpoints under `/api/...` with Token authentication.
- **Flask UI** (`lps_flask/`) — server-rendered Jinja templates. Forwards every request to the Django API using `requests`, attaching the user's API token from the Flask session.

```
Browser  ──HTTP──▶  Flask (:5000)  ──HTTP+Token──▶  Django (:8000)  ──ORM──▶  SQLite
```

The Flask app holds **no business state**. The only thing it stores in its own session is the Django auth token and a couple of UI flags (e.g. which order has been "claimed" in the demo).

## Heads-up for macOS users

Two macOS quirks can break the setup. Read these before you start:

**1. Case-insensitive filesystem.** macOS treats `LPS/` and `lps_flask/` as distinct, but earlier versions of this repo had `LPS/` and `lps/` which collided. If after cloning you see Flask files (`app.py`, `templates/`) inside `LPS/` instead of in their own folder, the clone got corrupted. Delete the folder and re-clone:

```bash
rm -rf Lottery-Purchase-System-Backend-
git clone https://github.com/chekwube-ononuju/Lottery-Purchase-System-Backend-.git
```

If it still collides, create a case-sensitive disk image via Disk Utility (File → New Image → Blank Image → Format: Mac OS Extended (Case-sensitive, Journaled)) and clone into `/Volumes/<your-image>` instead.

**2. Port 5000 is taken by AirPlay Receiver.** Flask defaults to port 5000, but macOS hijacks it. When you run `python app.py` and see "Address already in use", disable AirPlay Receiver:

System Settings → General → AirDrop & Handoff → toggle **AirPlay Receiver** off.

## Setup

You need Python 3.10 or higher (check with `python3 --version`). From the repo root:

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Django backend deps
pip install -r requirements.txt

# Flask UI deps
pip install -r lps_flask/requirements.txt
```

## Initialize the database

```bash
python manage.py migrate
python manage.py seed_lps
```

`seed_lps` creates the four default games (Powerball, Mega Millions, Lotto Texas, Texas Two Step), one scheduled draw per game, and a default admin:

- **username:** `admin`
- **password:** `admin123`
- **email:** `admin@lps.gov` (you can also log in via the Flask UI using this email)

## Run the system (two terminals)

**Terminal 1 — Django API:**

```bash
source venv/bin/activate
python manage.py runserver 8000
```

Sanity check: `curl http://127.0.0.1:8000/api/lottery-games/` should return JSON for the four games. The Django admin is at `http://127.0.0.1:8000/admin/`.

**Terminal 2 — Flask UI:**

```bash
source venv/bin/activate
cd lps_flask
python app.py
```

Then open `http://127.0.0.1:5000`. Log in with `admin@lps.gov` / `admin123` for admin, or register a new account for the customer flow.

## What works end-to-end

Verified by an automated 12-step test (now removed): register → login → browse → purchase 3 tickets → order confirmation → orders list → admin login → admin dashboard → run draw → winning numbers page → orders after draw → logout.

## API endpoints

All endpoints accept/return JSON. Authenticated endpoints require `Authorization: Token <key>` (the token is returned by `/api/login/`).

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/register/` | Create account, returns token |
| POST | `/api/login/` | Returns token + user info |
| POST | `/api/logout/` | Invalidates token |
| GET | `/api/profile/` | Current user info |
| GET | `/api/lottery-games/` | List of games |
| GET | `/api/lottery-games/<game_type>/` | Single game |
| POST | `/api/purchase-tickets/` | Buy 1–10 tickets in one order |
| GET | `/api/user-orders/` | Current user's orders (summary) |
| GET | `/api/orders/<id>/` | Single order with all tickets |
| GET | `/api/user-tickets/` | All ticket rows for current user |
| GET | `/api/winning-numbers/` | Published draw history |
| GET | `/api/admin-view/` | Stats — staff only |
| POST | `/api/admin-add-ticket/` | Create a game type — staff only |
| PUT | `/api/admin-update-ticket/` | Update price / prize — staff only |
| POST | `/api/admin-remove-ticket/` | Delete a game type — staff only |
| POST | `/api/admin-run-draw/` | Roll winning numbers + score tickets + publish — staff only |

## Notes on the integration

- **Username = email.** New accounts created from the Flask UI use the email as the Django username (Django requires a unique username field). The seeded admin keeps `admin` as username for convenience; the login form auto-tries that when you enter `admin@lps.gov`.
- **No CSRF in the API path.** The Flask app authenticates via Token, not session cookies, so DRF's CSRF check doesn't apply.
- **Claim flow is UI-side.** The original Flask app tracked "claimed" prizes in its JSON file. The Django side has no `claimed` field on `Order` yet, so the Flask app stores claims in its own session for the demo. Promoting this to a real DB column is a small follow-up.
- **Ticket numbers.** When a customer leaves the numbers field blank, `purchase_tickets` calls `generate_random_numbers(game_type)` server-side.

## Reset

```bash
rm db.sqlite3
python manage.py migrate
python manage.py seed_lps
```
