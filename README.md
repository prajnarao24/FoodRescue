# Food Rescue

A Flask web app that connects people with surplus food to people who need it — reducing food waste one donation at a time.

> Over 1.3 billion tons of food is wasted globally every year ,in India alone, roughly 68 million tons goes to waste annually, about 40% of what's produced. Food Rescue lets users donate surplus food, request available donations, track a personal inventory, get composting guidance, and find recipes from ingredients they already have.

---

## Features

- **User accounts** — sign up / log in with hashed passwords (Werkzeug), session-based auth
- **Donate food** — log surplus food (name, quantity, date, pickup/delivery) to a shared pool
- **Available Food** — browse donations from other users and request an item
- **Request workflow** — requesting an item marks it `pending`; the donor can **approve** or **decline** the request from their dashboard
- **Dashboard (`/home`)** — shows:
  - Your own donation history
  - Incoming requests on your donations (approve/decline)
  - Your outgoing requests and their status
  - Top Donors leaderboard (total quantity donated)
- **Email notifications** — donor and requester are emailed when a request is made (best-effort; silently skipped if email isn't configured)
- **Personal Inventory** — track food items you're storing, sorted by expiry date, with delete support
- **Waste Guide** — quick rule-based tool suggesting how to dispose of / compost a food item based on type, cooked state, and packaging
- **Fundraising / Donation** — simple monetary donation flow
- **Emergency & Achievements** — supporting pages for the app
- **Recipe Ideas (`/chat-bot`)** — enter ingredients you have, and the app queries [TheMealDB](https://www.themealdb.com/api.php) for matching recipes, ranked by how many of your ingredients each recipe uses

---

## Tech Stack

- **Backend:** Python, Flask
- **Database:** SQLite (via `sqlite3`, accessed with `sqlite3.Row` for dict-like rows)
- **Auth:** `werkzeug.security` (password hashing)
- **Email:** `smtplib` (Gmail SMTP)
- **External API:** [TheMealDB](https://www.themealdb.com/) for recipe search
- **Config:** `python-dotenv` for environment variables

---

## Project Structure

```
FOODRESCUE/
├── app.py                  # Main Flask application (routes & logic)
├── database.py             # Creates/migrates the SQLite schema
├── LoginData.db             # SQLite database file (generated)
├── requirements.txt
├── .env                     # Environment variables (not committed)
├── static/
│   └── main.css
└── templates/
    ├── base.html
    ├── login.html
    ├── signUp.html
    ├── home.html
    ├── inventory.html
    ├── waste.html
    ├── donate.html
    ├── fundraising_donation.html
    ├── emergency.html
    ├── achievements.html
    ├── stackFood.html
    ├── chat-bot.html
    └── _chatbot.html
```

---

## Database Schema

Defined and (auto-)migrated in `database.py`.

### `USERS`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | autoincrement |
| first_name | VARCHAR(50) | |
| last_name | VARCHAR(50) | |
| email | VARCHAR(120) | unique |
| password_hash | VARCHAR(255) | hashed via Werkzeug |
| door_no | VARCHAR(20) | used to scope personal inventory |

### `INVENTORY`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | autoincrement |
| foodname | VARCHAR(50) | |
| quantity | INTEGER | |
| expiry | DATE | |
| door_no | VARCHAR(20) | scopes items to a user's household |

### `DONATION`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | autoincrement |
| first_name / last_name / email | — | donor info |
| foodname | VARCHAR(50) | |
| quantity | INTEGER | |
| donation_date | DATE | |
| service | VARCHAR(15) | `pickup` or `delivery` |
| status | VARCHAR(15) | `available` → `pending` → `approved` |
| ordered_by_first_name / ordered_by_last_name / ordered_by_email | — | filled in when someone requests the item |

The order lifecycle is tracked entirely on this table (no separate `ORDERS` table): a donation moves through `available → pending → approved`, and a decline resets it back to `available`.

---

## Setup

### 1. Clone and install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment variables
Create a `.env` file in the project root:
```env
SECRET_KEY=your-random-secret-key
FOODRESCUE_EMAIL=your-gmail-address@gmail.com
FOODRESCUE_EMAIL_PASSWORD=your-gmail-app-password
```
- `SECRET_KEY` — used to sign Flask sessions. Required for sessions to persist across restarts.
- `FOODRESCUE_EMAIL` / `FOODRESCUE_EMAIL_PASSWORD` — optional. If omitted, email notifications are skipped (a message is printed to the console instead of failing).
- Use a [Gmail App Password](https://support.google.com/accounts/answer/185833), not your normal Gmail password.

### 3. Initialize the database
```bash
python database.py
```
This creates `LoginData.db` with the schema above. Safe to re-run — it only adds missing columns, it won't wipe existing data (except on first creation).

### 4. Run the app
```bash
python app.py
```
Visit **http://127.0.0.1:5000**

---

## Key Routes

| Route | Method(s) | Description |
|---|---|---|
| `/` | GET | Login page |
| `/login_validation` | POST | Validates credentials, starts session |
| `/signUp` | GET | Sign-up page |
| `/add_user` | POST | Creates a new user |
| `/logout` | GET | Clears session |
| `/home` | GET | Dashboard: donations, incoming/outgoing requests, leaderboard |
| `/add_donation` | POST | Logs a new donation |
| `/stackFood` | GET | Lists all `available` donations |
| `/order_food` | POST | Requests a donation (sets it to `pending`) |
| `/approve_order/<id>` | POST | Donor approves a pending request |
| `/decline_order/<id>` | POST | Donor declines; item returns to `available` |
| `/inventory` | GET, POST | View / add personal inventory items |
| `/delete/<id>` | POST | Remove an inventory item |
| `/waste` | GET, POST | Waste-disposal / composting guidance |
| `/donation` | GET | Donation info page |
| `/fundraising` | GET, POST | Monetary donation form |
| `/emergency` | GET | Emergency resources page |
| `/achievements` | GET | Achievements page |
| `/chat-bot` | GET | Recipe suggestions from ingredients (TheMealDB) |

All routes except auth ones are protected by a `@login_required` decorator that redirects to `/` if no session exists.

---
