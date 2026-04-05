"""
app.py
~~~~~~
main application — handles routes, auth, and donation management.

kept it as a single file because the app is small enough that
splitting into blueprints would be overkill. might refactor
if it grows.

run: python app.py
"""

import os
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, g, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
app.config["DATABASE"] = os.path.join(app.root_path, "food_rescue.db")


# ── database setup ─────────────────────────────────────────────

def get_db():
    """get database connection, create if doesn't exist."""
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """create tables if they don't exist."""
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT,
            role TEXT NOT NULL DEFAULT 'donor',
            organization TEXT,
            address TEXT,
            city TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_id INTEGER NOT NULL,
            food_type TEXT NOT NULL,
            description TEXT NOT NULL,
            quantity TEXT NOT NULL,
            pickup_address TEXT NOT NULL,
            city TEXT NOT NULL,
            expiry_time TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            claimed_by INTEGER,
            claimed_at TIMESTAMP,
            FOREIGN KEY (donor_id) REFERENCES users(id),
            FOREIGN KEY (claimed_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donation_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (donation_id) REFERENCES donations(id),
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        );
    """)
    db.commit()


# ── auth helpers ───────────────────────────────────────────────

def login_required(f):
    """redirect to login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    """get the logged-in user's data."""
    if "user_id" not in session:
        return None
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()


@app.context_processor
def inject_user():
    """make current_user available in all templates."""
    return {"current_user": get_current_user()}


# ── auth routes ────────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        role = request.form.get("role", "donor")
        phone = request.form.get("phone", "").strip()
        organization = request.form.get("organization", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()

        db = get_db()

        # check if email already exists
        if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("register"))

        db.execute(
            """INSERT INTO users (name, email, password, role, phone, organization, address, city)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, email, generate_password_hash(password), role, phone, organization, address, city)
        )
        db.commit()

        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_role"] = user["role"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("index"))


# ── main routes ────────────────────────────────────────────────

@app.route("/")
def index():
    db = get_db()
    # show some stats on the landing page
    stats = {
        "total_donations": db.execute("SELECT COUNT(*) FROM donations").fetchone()[0],
        "active_donations": db.execute("SELECT COUNT(*) FROM donations WHERE status = 'available'").fetchone()[0],
        "total_users": db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "claimed_donations": db.execute("SELECT COUNT(*) FROM donations WHERE status = 'claimed'").fetchone()[0],
    }
    # recent available donations for the homepage
    recent = db.execute(
        """SELECT d.*, u.name as donor_name, u.organization
           FROM donations d JOIN users u ON d.donor_id = u.id
           WHERE d.status = 'available' AND d.expiry_time > datetime('now')
           ORDER BY d.created_at DESC LIMIT 6"""
    ).fetchall()

    return render_template("index.html", stats=stats, recent_donations=recent)


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user = get_current_user()

    if user["role"] == "donor":
        # show donor's own donations
        donations = db.execute(
            """SELECT d.*, u.name as claimed_by_name
               FROM donations d LEFT JOIN users u ON d.claimed_by = u.id
               WHERE d.donor_id = ? ORDER BY d.created_at DESC""",
            (user["id"],)
        ).fetchall()
        return render_template("dashboard_donor.html", donations=donations)

    else:
        # show available donations for NGO/receiver
        available = db.execute(
            """SELECT d.*, u.name as donor_name, u.organization, u.phone as donor_phone
               FROM donations d JOIN users u ON d.donor_id = u.id
               WHERE d.status = 'available' AND d.expiry_time > datetime('now')
               ORDER BY d.created_at DESC"""
        ).fetchall()
        claimed = db.execute(
            """SELECT d.*, u.name as donor_name, u.organization
               FROM donations d JOIN users u ON d.donor_id = u.id
               WHERE d.claimed_by = ? ORDER BY d.claimed_at DESC""",
            (user["id"],)
        ).fetchall()
        return render_template("dashboard_receiver.html", available=available, claimed=claimed)


# ── donation CRUD ──────────────────────────────────────────────

@app.route("/donate", methods=["GET", "POST"])
@login_required
def create_donation():
    if request.method == "POST":
        db = get_db()
        user = get_current_user()

        food_type = request.form["food_type"]
        description = request.form["description"].strip()
        quantity = request.form["quantity"].strip()
        pickup_address = request.form["pickup_address"].strip()
        city = request.form["city"].strip()
        expiry_hours = int(request.form.get("expiry_hours", 24))

        expiry_time = datetime.now() + timedelta(hours=expiry_hours)

        db.execute(
            """INSERT INTO donations (donor_id, food_type, description, quantity,
                                      pickup_address, city, expiry_time)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user["id"], food_type, description, quantity, pickup_address, city,
             expiry_time.strftime("%Y-%m-%d %H:%M:%S"))
        )
        db.commit()
        flash("Donation listed! Someone in need will pick it up soon.", "success")
        return redirect(url_for("dashboard"))

    return render_template("create_donation.html")


@app.route("/donation/<int:donation_id>")
def view_donation(donation_id):
    db = get_db()
    donation = db.execute(
        """SELECT d.*, u.name as donor_name, u.organization, u.phone as donor_phone,
                  u.email as donor_email, c.name as claimed_by_name
           FROM donations d
           JOIN users u ON d.donor_id = u.id
           LEFT JOIN users c ON d.claimed_by = c.id
           WHERE d.id = ?""",
        (donation_id,)
    ).fetchone()

    if not donation:
        flash("Donation not found.", "danger")
        return redirect(url_for("index"))

    return render_template("view_donation.html", donation=donation)


@app.route("/donation/<int:donation_id>/claim", methods=["POST"])
@login_required
def claim_donation(donation_id):
    db = get_db()
    user = get_current_user()

    donation = db.execute("SELECT * FROM donations WHERE id = ?", (donation_id,)).fetchone()

    if not donation:
        flash("Donation not found.", "danger")
        return redirect(url_for("dashboard"))

    if donation["status"] != "available":
        flash("This donation is no longer available.", "warning")
        return redirect(url_for("dashboard"))

    if donation["donor_id"] == user["id"]:
        flash("You can't claim your own donation.", "warning")
        return redirect(url_for("dashboard"))

    db.execute(
        """UPDATE donations SET status = 'claimed', claimed_by = ?, claimed_at = datetime('now')
           WHERE id = ?""",
        (user["id"], donation_id)
    )
    db.commit()

    flash("Donation claimed! Contact the donor to arrange pickup.", "success")
    return redirect(url_for("view_donation", donation_id=donation_id))


@app.route("/donation/<int:donation_id>/cancel", methods=["POST"])
@login_required
def cancel_donation(donation_id):
    db = get_db()
    user = get_current_user()

    donation = db.execute("SELECT * FROM donations WHERE id = ?", (donation_id,)).fetchone()
    if donation and donation["donor_id"] == user["id"]:
        db.execute("DELETE FROM donations WHERE id = ?", (donation_id,))
        db.commit()
        flash("Donation removed.", "info")

    return redirect(url_for("dashboard"))


# ── browse donations ───────────────────────────────────────────

@app.route("/browse")
def browse():
    db = get_db()
    city_filter = request.args.get("city", "").strip()
    food_filter = request.args.get("food_type", "").strip()

    query = """SELECT d.*, u.name as donor_name, u.organization
               FROM donations d JOIN users u ON d.donor_id = u.id
               WHERE d.status = 'available' AND d.expiry_time > datetime('now')"""
    params = []

    if city_filter:
        query += " AND LOWER(d.city) LIKE ?"
        params.append(f"%{city_filter.lower()}%")

    if food_filter:
        query += " AND d.food_type = ?"
        params.append(food_filter)

    query += " ORDER BY d.created_at DESC"

    donations = db.execute(query, params).fetchall()

    cities = db.execute(
        "SELECT DISTINCT city FROM donations WHERE status = 'available' ORDER BY city"
    ).fetchall()

    return render_template("browse.html", donations=donations,
                           cities=cities, city_filter=city_filter, food_filter=food_filter)


# ── API endpoints (for future mobile app or frontend) ──────────

@app.route("/api/donations")
def api_donations():
    db = get_db()
    donations = db.execute(
        """SELECT d.id, d.food_type, d.description, d.quantity, d.city,
                  d.pickup_address, d.expiry_time, d.status, d.created_at,
                  u.name as donor_name, u.organization
           FROM donations d JOIN users u ON d.donor_id = u.id
           WHERE d.status = 'available' AND d.expiry_time > datetime('now')
           ORDER BY d.created_at DESC"""
    ).fetchall()

    return jsonify([dict(d) for d in donations])


@app.route("/api/stats")
def api_stats():
    db = get_db()
    return jsonify({
        "total_donations": db.execute("SELECT COUNT(*) FROM donations").fetchone()[0],
        "active": db.execute("SELECT COUNT(*) FROM donations WHERE status = 'available'").fetchone()[0],
        "claimed": db.execute("SELECT COUNT(*) FROM donations WHERE status = 'claimed'").fetchone()[0],
        "users": db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "donors": db.execute("SELECT COUNT(*) FROM users WHERE role = 'donor'").fetchone()[0],
        "receivers": db.execute("SELECT COUNT(*) FROM users WHERE role = 'receiver'").fetchone()[0],
    })


# ── profile ────────────────────────────────────────────────────

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    user = get_current_user()

    if request.method == "POST":
        name = request.form["name"].strip()
        phone = request.form.get("phone", "").strip()
        organization = request.form.get("organization", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()

        db.execute(
            """UPDATE users SET name=?, phone=?, organization=?, address=?, city=?
               WHERE id=?""",
            (name, phone, organization, address, city, user["id"])
        )
        db.commit()
        flash("Profile updated!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html")


# ── seed some demo data ───────────────────────────────────────

def seed_demo_data():
    """insert sample data so the app doesn't look empty on first run."""
    db = get_db()

    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        return  # already has data

    # create demo users
    demo_users = [
        ("Ravi Kumar", "ravi@example.com", generate_password_hash("password123"),
         "9876543210", "donor", "Kumar Restaurant", "45 MG Road", "Bengaluru"),
        ("Priya Sharma", "priya@example.com", generate_password_hash("password123"),
         "9876543211", "donor", "Sharma Caterers", "12 Anna Nagar", "Chennai"),
        ("Food For All NGO", "ngo@example.com", generate_password_hash("password123"),
         "9876543212", "receiver", "Food For All Foundation", "78 Residency Rd", "Bengaluru"),
        ("Helping Hands", "help@example.com", generate_password_hash("password123"),
         "9876543213", "receiver", "Helping Hands Trust", "34 T Nagar", "Chennai"),
    ]

    for u in demo_users:
        db.execute(
            "INSERT INTO users (name, email, password, phone, role, organization, address, city) VALUES (?,?,?,?,?,?,?,?)", u
        )

    # create demo donations
    demo_donations = [
        (1, "cooked_meal", "50 plates of biryani — leftover from a wedding event", "50 plates",
         "45 MG Road, Bengaluru", "Bengaluru",
         (datetime.now() + timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")),
        (1, "vegetables", "Fresh vegetables — carrots, tomatoes, spinach. Couldn't sell today",
         "15 kg", "45 MG Road, Bengaluru", "Bengaluru",
         (datetime.now() + timedelta(hours=18)).strftime("%Y-%m-%d %H:%M:%S")),
        (2, "cooked_meal", "30 lunch boxes from a cancelled corporate event",
         "30 boxes", "12 Anna Nagar, Chennai", "Chennai",
         (datetime.now() + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")),
        (2, "bakery", "Day-old bread and pastries from the bakery. Still fresh",
         "10 kg", "12 Anna Nagar, Chennai", "Chennai",
         (datetime.now() + timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")),
        (1, "fruits", "Bananas and apples — slightly overripe but perfectly edible",
         "8 kg", "45 MG Road, Bengaluru", "Bengaluru",
         (datetime.now() + timedelta(hours=10)).strftime("%Y-%m-%d %H:%M:%S")),
    ]

    for d in demo_donations:
        db.execute(
            """INSERT INTO donations (donor_id, food_type, description, quantity,
                                      pickup_address, city, expiry_time)
               VALUES (?, ?, ?, ?, ?, ?, ?)""", d
        )

    db.commit()
    print("[+] Demo data seeded — 4 users, 5 donations")


# ── run ────────────────────────────────────────────────────────

if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_demo_data()
    app.run(debug=True, port=5000)
