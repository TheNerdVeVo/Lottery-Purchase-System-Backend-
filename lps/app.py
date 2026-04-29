"""
Lottery Purchase System (LPS)
CS3365 - Team 9 - Phase 2
Flask backend with JSON file persistence.
"""
import json
import os
import random
import uuid
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash

app = Flask(__name__)
app.secret_key = "team9-lps-secret"

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")


# ---------- Persistence ----------
def load_db():
    if not os.path.exists(DATA_FILE):
        seed_db()
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_db(db):
    with open(DATA_FILE, "w") as f:
        json.dump(db, f, indent=2, default=str)


def seed_db():
    db = {
        "users": {
            "admin@lps.gov": {
                "user_id": str(uuid.uuid4()),
                "name": "System Administrator",
                "email": "admin@lps.gov",
                "address": "Texas Lottery HQ, Austin TX",
                "phone": "5125551000",
                "password_hash": hash_password("admin123"),
                "role": "admin",
            }
        },
        "tickets": {
            "PB":  {"ticket_id": "PB",  "name": "Power Ball",     "price": 2.00, "winning_amount": 50000000.00, "active": True},
            "MM":  {"ticket_id": "MM",  "name": "Mega Millions",  "price": 2.00, "winning_amount": 40000000.00, "active": True},
            "LT":  {"ticket_id": "LT",  "name": "Lotto Texas",    "price": 1.00, "winning_amount": 10000000.00, "active": True},
            "TTS": {"ticket_id": "TTS", "name": "Texas Two Step", "price": 1.50, "winning_amount":  1000000.00, "active": True},
        },
        "orders": [],
        "draws": {
            "PB":  {"numbers": [7, 14, 22, 31, 49],  "draw_date": "2026-04-13"},
            "MM":  {"numbers": [3, 11, 25, 38, 42],  "draw_date": "2026-04-13"},
            "LT":  {"numbers": [9, 17, 23, 30, 45],  "draw_date": "2026-04-13"},
            "TTS": {"numbers": [2, 19, 27, 33, 41],  "draw_date": "2026-04-13"},
        },
        "draw_history": [],
        "stats": {"tickets_sold": 0, "revenue": 0.0},
    }
    with open(DATA_FILE, "w") as f:
        json.dump(db, f, indent=2)


# ---------- Helpers ----------
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "email" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("Access denied.", "error")
                return redirect(url_for("home"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def current_user(db):
    return db["users"].get(session.get("email"))


def calc_winnings(picked, drawn, ticket_amount):
    matches = len(set(picked) & set(drawn))
    pct = {5: 1.0, 4: 0.20, 3: 0.05, 2: 0.01}.get(matches, 0.0)
    return matches, ticket_amount * pct


def evaluate_order(order, db):
    """Compute winnings for each ticket in an order based on the latest draw."""
    ticket_def = db["tickets"].get(order["ticket_type"])
    if not ticket_def:
        return order
    draw = db["draws"].get(order["ticket_type"])
    if not draw:
        return order
    total_win = 0.0
    is_winner = False
    for t in order["tickets"]:
        matches, win = calc_winnings(t["numbers"], draw["numbers"], ticket_def["winning_amount"])
        t["matches"] = matches
        t["winnings"] = win
        t["winning_numbers"] = draw["numbers"]
        if matches >= 2:
            is_winner = True
        total_win += win
    order["total_winnings"] = total_win
    order["status"] = "winner" if is_winner else "no_win"
    return order


# ---------- Auth Routes ----------
@app.route("/")
def index():
    if "email" in session:
        return redirect(url_for("home"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        db = load_db()
        email = request.form["email"].strip().lower()
        if email in db["users"]:
            flash("Email already registered.", "error")
            return redirect(url_for("register"))
        db["users"][email] = {
            "user_id": str(uuid.uuid4()),
            "name": request.form["name"].strip(),
            "email": email,
            "address": request.form["address"].strip(),
            "phone": request.form["phone"].strip(),
            "password_hash": hash_password(request.form["password"]),
            "role": "customer",
        }
        save_db(db)
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = load_db()
        email = request.form["email"].strip().lower()
        pw = request.form["password"]
        user = db["users"].get(email)
        if user and user["password_hash"] == hash_password(pw):
            session["email"] = email
            session["role"] = user["role"]
            session["name"] = user["name"]
            return redirect(url_for("admin_dashboard") if user["role"] == "admin" else url_for("home"))
        flash("Invalid credentials.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- Customer Routes ----------
@app.route("/home")
@login_required()
def home():
    return render_template("home.html", name=session.get("name"))


@app.route("/browse")
@login_required()
def browse():
    db = load_db()
    q = request.args.get("q", "").strip().lower()
    tickets = [t for t in db["tickets"].values() if t["active"]]
    if q:
        tickets = [t for t in tickets if q in t["name"].lower()]
    return render_template("browse.html", tickets=tickets, q=q)


@app.route("/ticket/<ticket_id>")
@login_required()
def ticket_detail(ticket_id):
    db = load_db()
    ticket = db["tickets"].get(ticket_id)
    if not ticket or not ticket["active"]:
        flash("Ticket not found.", "error")
        return redirect(url_for("browse"))
    draw = db["draws"].get(ticket_id)
    next_draw = (datetime.fromisoformat(draw["draw_date"]) + timedelta(days=7)).date().isoformat() if draw else "TBA"
    return render_template("ticket_detail.html", ticket=ticket, next_draw=next_draw)


@app.route("/purchase/<ticket_id>", methods=["GET", "POST"])
@login_required()
def purchase(ticket_id):
    db = load_db()
    ticket = db["tickets"].get(ticket_id)
    if not ticket or not ticket["active"]:
        flash("Ticket not available.", "error")
        return redirect(url_for("browse"))
    if request.method == "POST":
        try:
            qty = int(request.form.get("quantity", 1))
        except ValueError:
            qty = 1
        if qty < 1 or qty > 10:
            flash("You can purchase between 1 and 10 tickets.", "error")
            return redirect(url_for("purchase", ticket_id=ticket_id))
        payment = request.form.get("payment_method")
        if payment not in {"PayPal", "Venmo", "Bank"}:
            flash("Select a valid payment method.", "error")
            return redirect(url_for("purchase", ticket_id=ticket_id))
        all_tickets = []
        for i in range(qty):
            mode = request.form.get(f"mode_{i}", "auto")
            if mode == "manual":
                try:
                    nums = sorted({int(request.form.get(f"n{i}_{j}")) for j in range(5)})
                except (TypeError, ValueError):
                    flash(f"Ticket {i+1}: enter 5 valid numbers.", "error")
                    return redirect(url_for("purchase", ticket_id=ticket_id))
                if len(nums) != 5 or any(n < 1 or n > 50 for n in nums):
                    flash(f"Ticket {i+1}: numbers must be 5 unique values between 1-50.", "error")
                    return redirect(url_for("purchase", ticket_id=ticket_id))
            else:
                nums = sorted(random.sample(range(1, 51), 5))
            all_tickets.append({
                "confirmation": str(uuid.uuid4())[:8].upper(),
                "numbers": nums,
            })
        order = {
            "order_id": str(uuid.uuid4())[:12].upper(),
            "user_email": session["email"],
            "ticket_type": ticket_id,
            "ticket_name": ticket["name"],
            "unit_price": ticket["price"],
            "quantity": qty,
            "total_cost": round(ticket["price"] * qty, 2),
            "payment_method": payment,
            "purchase_date": datetime.now().isoformat(),
            "tickets": all_tickets,
            "status": "pending_draw",
            "total_winnings": 0.0,
            "claimed": False,
        }
        db["orders"].append(order)
        db["stats"]["tickets_sold"] += qty
        db["stats"]["revenue"] = round(db["stats"]["revenue"] + order["total_cost"], 2)
        save_db(db)
        return redirect(url_for("order_confirmation", order_id=order["order_id"]))
    return render_template("purchase.html", ticket=ticket)


@app.route("/order/<order_id>")
@login_required()
def order_confirmation(order_id):
    db = load_db()
    order = next((o for o in db["orders"] if o["order_id"] == order_id), None)
    if not order or order["user_email"] != session["email"]:
        flash("Order not found.", "error")
        return redirect(url_for("orders"))
    return render_template("order_confirmation.html", order=order)


@app.route("/orders")
@login_required()
def orders():
    db = load_db()
    user_orders = [o for o in db["orders"] if o["user_email"] == session["email"]]
    user_orders = [evaluate_order(o, db) for o in user_orders]
    user_orders.sort(key=lambda o: o["purchase_date"], reverse=True)
    save_db(db)
    return render_template("orders.html", orders=user_orders)


@app.route("/order_detail/<order_id>")
@login_required()
def order_detail(order_id):
    db = load_db()
    order = next((o for o in db["orders"] if o["order_id"] == order_id), None)
    if not order or order["user_email"] != session["email"]:
        flash("Order not found.", "error")
        return redirect(url_for("orders"))
    order = evaluate_order(order, db)
    save_db(db)
    return render_template("order_detail.html", order=order)


@app.route("/claim/<order_id>", methods=["POST"])
@login_required()
def claim(order_id):
    db = load_db()
    order = next((o for o in db["orders"] if o["order_id"] == order_id), None)
    if not order or order["user_email"] != session["email"]:
        return jsonify({"ok": False, "msg": "Not found"}), 404
    if order["claimed"]:
        return jsonify({"ok": False, "msg": "Already claimed"}), 400
    if order["total_winnings"] >= 600:
        return jsonify({"ok": False, "msg": "Prizes of $600 or more must be claimed at a local lottery claiming center."}), 400
    order["claimed"] = True
    order["claimed_to"] = order["payment_method"]
    save_db(db)
    return jsonify({"ok": True, "msg": f"${order['total_winnings']:.2f} deposited to your {order['payment_method']} account."})


@app.route("/winning_numbers")
@login_required()
def winning_numbers():
    db = load_db()
    rows = []
    for tid, draw in db["draws"].items():
        if tid in db["tickets"]:
            rows.append({
                "ticket_id": tid,
                "ticket_name": db["tickets"][tid]["name"],
                "numbers": draw["numbers"],
                "draw_date": draw["draw_date"],
            })
    return render_template("winning_numbers.html", draws=rows)


@app.route("/profile")
@login_required()
def profile():
    db = load_db()
    user = current_user(db)
    return render_template("profile.html", user=user)


# ---------- Admin Routes ----------
@app.route("/admin")
@login_required(role="admin")
def admin_dashboard():
    db = load_db()
    return render_template("admin_dashboard.html",
                           stats=db["stats"],
                           total_users=len([u for u in db["users"].values() if u["role"] == "customer"]),
                           total_orders=len(db["orders"]))


@app.route("/admin/tickets")
@login_required(role="admin")
def admin_tickets():
    db = load_db()
    return render_template("admin_tickets.html", tickets=list(db["tickets"].values()))


@app.route("/admin/tickets/add", methods=["GET", "POST"])
@login_required(role="admin")
def admin_add_ticket():
    if request.method == "POST":
        db = load_db()
        tid = request.form["ticket_id"].strip().upper()
        if tid in db["tickets"]:
            flash("Ticket ID already exists.", "error")
            return redirect(url_for("admin_add_ticket"))
        db["tickets"][tid] = {
            "ticket_id": tid,
            "name": request.form["name"].strip(),
            "price": float(request.form["price"]),
            "winning_amount": float(request.form["winning_amount"]),
            "active": True,
        }
        db["draws"][tid] = {"numbers": sorted(random.sample(range(1, 51), 5)),
                            "draw_date": datetime.now().date().isoformat()}
        save_db(db)
        flash(f"Ticket '{request.form['name']}' added.", "success")
        return redirect(url_for("admin_tickets"))
    return render_template("admin_ticket_form.html", action="Add", ticket=None)


@app.route("/admin/tickets/edit/<ticket_id>", methods=["GET", "POST"])
@login_required(role="admin")
def admin_edit_ticket(ticket_id):
    db = load_db()
    ticket = db["tickets"].get(ticket_id)
    if not ticket:
        flash("Ticket not found.", "error")
        return redirect(url_for("admin_tickets"))
    if request.method == "POST":
        ticket["name"] = request.form["name"].strip()
        ticket["price"] = float(request.form["price"])
        ticket["winning_amount"] = float(request.form["winning_amount"])
        save_db(db)
        flash("Ticket updated.", "success")
        return redirect(url_for("admin_tickets"))
    return render_template("admin_ticket_form.html", action="Edit", ticket=ticket)


@app.route("/admin/tickets/remove/<ticket_id>", methods=["POST"])
@login_required(role="admin")
def admin_remove_ticket(ticket_id):
    db = load_db()
    if ticket_id in db["tickets"]:
        db["tickets"][ticket_id]["active"] = False
        save_db(db)
        flash("Ticket removed.", "success")
    return redirect(url_for("admin_tickets"))


@app.route("/admin/draw", methods=["GET", "POST"])
@login_required(role="admin")
def admin_draw():
    db = load_db()
    if request.method == "POST":
        tid = request.form["ticket_id"]
        if tid in db["tickets"]:
            new_nums = sorted(random.sample(range(1, 51), 5))
            old = db["draws"].get(tid, {})
            if old:
                db["draw_history"].append({"ticket_id": tid, **old})
            db["draws"][tid] = {"numbers": new_nums, "draw_date": datetime.now().date().isoformat()}
            save_db(db)
            flash(f"New draw for {db['tickets'][tid]['name']}: {new_nums}", "success")
        return redirect(url_for("admin_draw"))
    draws = []
    for tid, draw in db["draws"].items():
        if tid in db["tickets"]:
            draws.append({"ticket_id": tid, "ticket_name": db["tickets"][tid]["name"], **draw})
    return render_template("admin_draw.html", draws=draws)


@app.route("/admin/reset", methods=["POST"])
@login_required(role="admin")
def admin_reset():
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    seed_db()
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    if not os.path.exists(DATA_FILE):
        seed_db()
    app.run(debug=True, port=5000)
