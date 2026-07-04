# Food Rescue — setup

## 1. Install dependencies
```
pip install -r requirements.txt
```

## 2. Set environment variables
The app reads secrets from the environment instead of hardcoding them:

```
export SECRET_KEY="a-long-random-string"
export FOODRESCUE_EMAIL="youraddress@gmail.com"          # optional — for order notifications
export FOODRESCUE_EMAIL_PASSWORD="an-app-password"        # use a Gmail App Password, not your real password
export SPOONACULAR_API_KEY="your-spoonacular-key"          # optional — for the recipe finder page
```
If you skip the email or Spoonacular vars, those two features degrade gracefully (no crash — you'll just see a message that they're not configured).

On Windows (PowerShell): `$env:SECRET_KEY="..."`

## 3. Create the database
```
python database.py
```
**If you have an old `LoginData.db` from before this rewrite, delete it first.** The schema changed (passwords are now hashed in a `password_hash` column, and tables use proper auto-increment `id` primary keys instead of `email` as a primary key), so old rows won't line up with the new columns.

## 4. Run
```
python app.py
```

## What changed from the original version
- **Auth**: login state now lives in a signed Flask session cookie, not in the URL (`/home?fname=...`) — the old version leaked your name and email into browser history and server logs.
- **Passwords**: hashed with Werkzeug (`generate_password_hash` / `check_password_hash`) instead of stored in plaintext.
- **Database**: `USERS.email` is now `UNIQUE` instead of the primary key; `DONATION` and `INVENTORY` got real auto-increment `id` columns, so one person can make more than one donation and items can be deleted precisely instead of by name.
- **Waste form bug**: the checkbox logic used to check for `'off'`/`'on'` string values that HTML checkboxes never actually send. Fixed to check whether the field is present at all.
- **Secrets**: Gmail credentials and the Spoonacular API key are read from environment variables, not hardcoded in `app.py` or exposed in client-side JavaScript.
- **Filename bugs**: `chaat-bot.html` → `chat-bot.html`, `achievement.html` → `achievements.html`, `fundraisong_donation.html` → `fundraising_donation.html`, `style.css` → consolidated into `static/main.css`, all now matching what `app.py` actually calls.
- **Dead dependencies removed**: the rawgit.com QR library (shut down in 2019), source.unsplash.com hotlinked images (discontinued API), and the missing `chatbot.js` reference are gone — QR codes now use a live API, and the chatbot widget is a small vanilla-JS include (`_chatbot.html`).
- **`bank.html`** wasn't wired into any route or nav link in what you sent me, so it isn't part of this rebuild. Let me know if you want it turned into a real page and I'll add it in.
