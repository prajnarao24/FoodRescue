import os
import sqlite3
import smtplib
from contextlib import contextmanager
from functools import wraps
from email.message import EmailMessage

from dotenv import load_dotenv
load_dotenv()

import requests
from flask import Flask, render_template, request, redirect, flash, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- Secrets: read from environment, never hardcode ---
# Set a real SECRET_KEY in your environment before deploying. This random
# fallback is fine for local dev only (sessions won't survive a restart).
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

EMAIL_ADDRESS = os.environ.get("FOODRESCUE_EMAIL")
EMAIL_PASSWORD = os.environ.get("FOODRESCUE_EMAIL_PASSWORD")

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LoginData.db")


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------
@contextmanager
def get_db():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()

def init_db():
    """Create tables if they don't exist yet. Safe to run on every startup."""
    with get_db() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS USERS (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name    VARCHAR(50) NOT NULL,
            last_name     VARCHAR(50) NOT NULL,
            email         VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            door_no       VARCHAR(20) NOT NULL
        )
        """)

        db.execute("""
        CREATE TABLE IF NOT EXISTS INVENTORY (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            foodname VARCHAR(50) NOT NULL,
            quantity INTEGER NOT NULL,
            expiry   DATE NOT NULL,
            door_no  VARCHAR(20) NOT NULL
        )
        """)

        db.execute("""
        CREATE TABLE IF NOT EXISTS DONATION (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name            VARCHAR(50) NOT NULL,
            last_name             VARCHAR(50) NOT NULL,
            email                 VARCHAR(120) NOT NULL,
            foodname              VARCHAR(50) NOT NULL,
            quantity              INTEGER NOT NULL,
            donation_date         DATE NOT NULL,
            service               VARCHAR(15) NOT NULL,
            status                VARCHAR(15) NOT NULL DEFAULT 'available',
            ordered_by_first_name VARCHAR(50),
            ordered_by_last_name  VARCHAR(50),
            ordered_by_email      VARCHAR(120)
        )
        """)

        existing_columns = {row[1] for row in db.execute("PRAGMA table_info(DONATION)").fetchall()}
        migration_columns = {
            "status": "VARCHAR(15) NOT NULL DEFAULT 'available'",
            "ordered_by_first_name": "VARCHAR(50)",
            "ordered_by_last_name": "VARCHAR(50)",
            "ordered_by_email": "VARCHAR(120)",
        }
        for column, definition in migration_columns.items():
            if column not in existing_columns:
                db.execute(f"ALTER TABLE DONATION ADD COLUMN {column} {definition}")


init_db()
# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "email" not in session:
            flash("Please log in to continue.")
            return redirect("/")
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.route("/")
def login():
    #if "email" in session:
     #   return redirect("/home")
    return render_template("login.html")


@app.route("/login_validation", methods=["POST"])
def login_validation():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    with get_db() as db:
        user = db.execute("SELECT * FROM USERS WHERE email = ?", (email,)).fetchone()

    if user and check_password_hash(user["password_hash"], password):
        session["fname"] = user["first_name"]
        session["lname"] = user["last_name"]
        session["email"] = user["email"]
        session["door_no"] = user["door_no"]
        return redirect("/home")

    flash("Invalid email or password.")
    return redirect("/")


@app.route("/signUp")
def signUp():
    return render_template("signUp.html")


@app.route("/add_user", methods=["POST"])
def add_user():
    fname = (request.form.get("fname") or "").strip()
    lname = (request.form.get("lname") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    door_no = (request.form.get("door_no") or "").strip()

    if not all([fname, lname, email, password, door_no]):
        flash("All fields are required.")
        return redirect("/signUp")

    if len(password) < 8:
        flash("Password must be at least 8 characters.")
        return redirect("/signUp")

    with get_db() as db:
        existing = db.execute("SELECT 1 FROM USERS WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("That email is already registered. Please log in.")
            return redirect("/")

        db.execute(
            "INSERT INTO USERS (first_name, last_name, email, password_hash, door_no) VALUES (?, ?, ?, ?, ?)",
            (fname, lname, email, generate_password_hash(password), door_no),
        )

    flash("Sign-up successful! Please log in.")
    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.")
    return redirect("/")


# ---------------------------------------------------------------------------
# Home / dashboard
# ---------------------------------------------------------------------------
@app.route("/home")
@login_required
def home():
    email = session["email"]

    with get_db() as db:
        donations = db.execute(
            "SELECT foodname, quantity, donation_date, service FROM DONATION WHERE email = ? ORDER BY id DESC",
            (email,),
        ).fetchall()

        incoming_requests = db.execute(
            "SELECT * FROM DONATION WHERE email = ? AND status = 'pending' ORDER BY id DESC",
            (email,),
        ).fetchall()

        my_orders = db.execute(
            """
            SELECT
                foodname, quantity, status,
                first_name AS donor_first_name,
                last_name AS donor_last_name,
                email AS donor_email
            FROM DONATION
            WHERE ordered_by_email = ?
            ORDER BY id DESC
            """,
            (email,),
        ).fetchall()

        leaderboard = db.execute(
            """
            SELECT first_name, last_name, SUM(quantity) AS total_donations
            FROM DONATION
            GROUP BY first_name, last_name
            ORDER BY total_donations DESC
            LIMIT 10
            """
        ).fetchall()

    return render_template(
        "home.html",
        fname=session["fname"],
        lname=session["lname"],
        email=email,
        donations=donations,
        incoming_requests=incoming_requests,
        my_orders=my_orders,
        leaderboard=leaderboard,
    )

@app.route("/add_donation", methods=["POST"])
@login_required
def add_donation():
    foodname = (request.form.get("foodname") or "").strip()
    quantity = request.form.get("quantity")
    donation_date = request.form.get("donation_date")
    service = request.form.get("service")

    if not all([foodname, quantity, donation_date, service]):
        flash("Please fill in every field.")
        return redirect("/home")

    try:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        flash("Quantity must be a positive number.")
        return redirect("/home")

    with get_db() as db:
        db.execute(
            "INSERT INTO DONATION (first_name, last_name, email, foodname, quantity, donation_date, service) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session["fname"], session["lname"], session["email"], foodname, quantity, donation_date, service),
        )

    flash("Donation added successfully!")
    return redirect("/home")


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
@app.route("/inventory", methods=["GET", "POST"])
@login_required
def inventory():
    door_no = session["door_no"]

    if request.method == "POST":
        foodname = (request.form.get("food-name") or "").strip()
        quantity = request.form.get("quantity")
        expiry_date = request.form.get("expiry-date")

        if not all([foodname, quantity, expiry_date]):
            flash("Please fill in every field.")
            return redirect(url_for("inventory"))

        with get_db() as db:
            db.execute(
                "INSERT INTO INVENTORY (foodname, quantity, expiry, door_no) VALUES (?, ?, ?, ?)",
                (foodname, quantity, expiry_date, door_no),
            )
        flash("Item added to your inventory.")
        return redirect(url_for("inventory"))

    with get_db() as db:
        items = db.execute(
            "SELECT * FROM INVENTORY WHERE door_no = ? ORDER BY expiry ASC", (door_no,)
        ).fetchall()

    return render_template("inventory.html", items=items)


@app.route("/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_id):
    with get_db() as db:
        db.execute(
            "DELETE FROM INVENTORY WHERE id = ? AND door_no = ?", (item_id, session["door_no"])
        )
    return redirect("/inventory")


# ---------------------------------------------------------------------------
# Waste categorization
# ---------------------------------------------------------------------------
@app.route("/waste", methods=["GET", "POST"])
@login_required
def waste():
    result = None
    if request.method == "POST":
        food_item = request.form.get("food_item")
        is_cooked = request.form.get("cooked") == "yes"
        # A checkbox sends 'on' when checked and is simply absent when not -
        # never 'off'. Checking for None (unchecked) is the correct test.
        is_packed = request.form.get("plastic_packed") is not None
        amount = request.form.get("food_amount")

        if is_packed:
            result = f"Remove the plastic packaging from {amount} of {food_item} before doing anything else."
        elif food_item == "meat" or is_cooked:
            result = f"{amount} of {food_item} should be disposed of carefully — do not compost cooked or meat items."
        elif food_item in ("vegetables", "fruits"):
            result = f"{amount} of {food_item} can be composted."
        else:
            result = f"{amount} of {food_item} does not fit our composting guidelines. Dispose of it appropriately."

    return render_template("waste.html", result=result)


# ---------------------------------------------------------------------------
# Fundraising
# ---------------------------------------------------------------------------
@app.route("/donation")
@login_required
def donation():
    return render_template("donate.html")


@app.route("/fundraising", methods=["GET", "POST"])
@login_required
def fundraising():
    donation_amount = None
    if request.method == "POST":
        raw_amount = request.form.get("donation-amount")
        try:
            amount = float(raw_amount)
            if amount <= 0:
                raise ValueError
            donation_amount = f"{amount:.2f}"
        except (TypeError, ValueError):
            flash("Please enter a valid donation amount.")
            return redirect("/fundraising")

    return render_template("fundraising_donation.html", donation_amount=donation_amount)


@app.route("/emergency")
@login_required
def emergency():
    return render_template("emergency.html")


@app.route("/achievements")
@login_required
def achievements():
    return render_template("achievements.html")


# ---------------------------------------------------------------------------
# Available food / ordering
# ---------------------------------------------------------------------------
@app.route("/stackFood")
@login_required
def stack_food():
    with get_db() as db:
        items = db.execute(
            "SELECT id, foodname, quantity, email FROM DONATION WHERE status = 'available' ORDER BY id DESC"
        ).fetchall()
    return render_template("stackFood.html", items=items)

@app.route("/order_food", methods=["POST"])
@login_required
def order_food():
    donation_id = request.form.get("donation_id")

    with get_db() as db:
        donation_row = db.execute(
            "SELECT * FROM DONATION WHERE id = ? AND status = 'available'", (donation_id,)
        ).fetchone()

        if not donation_row:
            flash("That item is no longer available.")
            return redirect("/stackFood")

        db.execute(
            """
            UPDATE DONATION
            SET status = 'pending',
                ordered_by_first_name = ?,
                ordered_by_last_name = ?,
                ordered_by_email = ?
            WHERE id = ?
            """,
            (session["fname"], session["lname"], session["email"], donation_id),
        )

    send_email_notifications(
        donation_row["foodname"],
        donation_row["email"],
        f"{session['fname']} {session['lname']}",
        session["email"],
    )
    flash(f"Request sent for {donation_row['foodname']}! The donor will need to approve it.")
    return redirect("/stackFood")


@app.route("/approve_order/<int:donation_id>", methods=["POST"])
@login_required
def approve_order(donation_id):
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM DONATION WHERE id = ? AND email = ?",
            (donation_id, session["email"]),
        ).fetchone()

        if not row:
            flash("That request no longer exists.")
            return redirect("/home")

        db.execute(
            "UPDATE DONATION SET status = 'approved' WHERE id = ?", (donation_id,)
        )

    flash(f"You approved the request for {row['foodname']}.")
    return redirect("/home")


@app.route("/decline_order/<int:donation_id>", methods=["POST"])
@login_required
def decline_order(donation_id):
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM DONATION WHERE id = ? AND email = ?",
            (donation_id, session["email"]),
        ).fetchone()

        if not row:
            flash("That request no longer exists.")
            return redirect("/home")

        db.execute(
            """
            UPDATE DONATION
            SET status = 'available',
                ordered_by_first_name = NULL,
                ordered_by_last_name = NULL,
                ordered_by_email = NULL
            WHERE id = ?
            """,
            (donation_id,),
        )

    flash(f"You declined the request for {row['foodname']}. It's available again.")
    return redirect("/home")






def send_email_notifications(food_name, donor_email, recipient_name, recipient_email):
    """Best-effort email notification. Silently skips if email isn't configured."""

    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("Email not configured (set FOODRESCUE_EMAIL / FOODRESCUE_EMAIL_PASSWORD) — skipping notification.")
        return

    subject = f"Food Order Update: {food_name}"

    donor_message = f"""
Hello,

Your donated food item "{food_name}" has been ordered.

Recipient Details
-----------------
Name : {recipient_name}
Email: {recipient_email}

Please contact the recipient to coordinate the pickup or delivery.

Thank you for helping reduce food waste!

Regards,
Food Rescue Team
"""

    recipient_message = f"""
Hello {recipient_name},

You have successfully ordered "{food_name}".

The donor has been notified of your order and will be able to contact you using your email address to arrange the pickup or delivery.

Thank you for using Food Rescue!

Regards,
Food Rescue Team
"""

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

            for recipient, body in (
                (donor_email, donor_message),
                (recipient_email, recipient_message),
            ):
                msg = EmailMessage()
                msg.set_content(body)
                msg["Subject"] = subject
                msg["From"] = EMAIL_ADDRESS
                msg["To"] = recipient

                server.send_message(msg)

    except Exception as exc:
        print(f"Error sending email: {exc}")
# ---------------------------------------------------------------------------
# Recipe finder (Spoonacular proxy — key stays server-side)
# ---------------------------------------------------------------------------
@app.route("/chat-bot")
@login_required
def chat_bot():
    query = request.args.get("ingredients", "").strip()

    recipes = []
    error = None

    if query:
        ingredients = [
            i.strip().lower()
            for i in query.split(",")
            if i.strip()
        ]

        meal_counts = {}

        try:
            for ingredient in ingredients:

                response = requests.get(
                    "https://www.themealdb.com/api/json/v1/1/filter.php",
                    params={"i": ingredient},
                    timeout=8,
                )

                response.raise_for_status()

                meals = response.json().get("meals")

                if meals:

                    for meal in meals:
                        meal_id = meal["idMeal"]

                        if meal_id not in meal_counts:
                            meal_counts[meal_id] = {
                                "meal": meal,
                                "count": 0,
                            }

                        meal_counts[meal_id]["count"] += 1

            recipes = sorted(
                meal_counts.values(),
                key=lambda x: x["count"],
                reverse=True,
            )

            recipes = [item["meal"] for item in recipes]

            if not recipes:
                error = "No recipes found."

        except requests.RequestException:
            error = "Unable to connect to recipe service."

    return render_template(
        "chat-bot.html",
        query=query,
        recipes=recipes,
        error=error,
    )
if __name__ == "__main__":
    app.run(debug=False)
