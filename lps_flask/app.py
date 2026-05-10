"""
Lottery Purchase System (LPS) - Flask UI
CS3365 Team 9 - Phase 3

Phase 3 adds:
- In-app notifications (bell + list page)
- Wallet / account balance (top up, deduct on purchase)
- Weekly spending limits
- Admin analytics dashboard with charts
- Persistent prize claim flow
- Manual force-win (admin can pick winning numbers)
"""
import os
from functools import wraps

import requests
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify,
)

app = Flask(__name__)
app.secret_key = "team9-lps-secret"

API_BASE = os.environ.get("LPS_API_BASE", "http://127.0.0.1:8000/api")
HTTP_TIMEOUT = 10


# ---------- API client ----------

def _headers():
    h = {"Accept": "application/json"}
    tok = session.get("token")
    if tok:
        h["Authorization"] = f"Token {tok}"
    return h


def api_get(path, **kw):
    return requests.get(f"{API_BASE}{path}", headers=_headers(), timeout=HTTP_TIMEOUT, **kw)


def api_post(path, json=None, **kw):
    return requests.post(f"{API_BASE}{path}", json=json, headers=_headers(),
                         timeout=HTTP_TIMEOUT, **kw)


def api_put(path, json=None, **kw):
    return requests.put(f"{API_BASE}{path}", json=json, headers=_headers(),
                        timeout=HTTP_TIMEOUT, **kw)


# ---------- helpers ----------

def _ticket_to_template(g):
    return {
        "ticket_id": g["game_type"],
        "name": g["name"],
        "price": float(g["ticket_price"]),
        "winning_amount": float(g["prize_amount"]),
        "active": True,
    }


def _all_games():
    r = api_get("/lottery-games/")
    return r.json() if r.ok else []


def _name_for(game_type, games):
    for g in games:
        if g["game_type"] == game_type:
            return g["name"]
    return game_type


def _price_for(game_type, games):
    for g in games:
        if g["game_type"] == game_type:
            return float(g["ticket_price"])
    return 0.0


# ---------- decorators ----------

def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("token"):
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("Admin access only.", "error")
                return redirect(url_for("home"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ---------- context processor: notification badge on every page ----------

@app.context_processor
def inject_globals():
    unread = 0
    if session.get("token"):
        try:
            r = api_get("/notifications/unread-count/")
            if r.ok:
                unread = r.json().get("unread", 0)
        except Exception:
            pass
    return {"unread_notifications": unread}


# ---------- public auth ----------

@app.route("/")
def index():
    return redirect(url_for("home" if session.get("token") else "login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if not all([full_name, email, address, phone, password]):
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        first, _, last = full_name.partition(" ")
        if not last:
            last = first

        r = api_post("/register/", json={
            "username": email, "email": email,
            "first_name": first, "last_name": last,
            "home_address": address, "phone_number": phone,
            "password1": password, "password2": password,
        })
        if r.status_code == 201:
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))

        try:
            errors = r.json()
            first_msg = next(iter(errors.values()))
            if isinstance(first_msg, list):
                first_msg = first_msg[0]
        except Exception:
            first_msg = "Registration failed."
        flash(str(first_msg), "error")
        return redirect(url_for("register"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        candidates = [email]
        if email == "admin@lps.gov":
            candidates.insert(0, "admin")

        for username in candidates:
            r = api_post("/login/", json={"username": username, "password": password})
            if r.ok:
                d = r.json()
                session["token"] = d["token"]
                session["username"] = d["username"]
                session["email"] = d.get("email", email)
                session["name"] = (f"{d.get('first_name','')} {d.get('last_name','')}".strip()
                                   or d["username"])
                session["role"] = "admin" if d.get("is_admin") else "user"
                flash("Welcome back!", "success")
                return redirect(url_for("admin_dashboard") if session["role"] == "admin"
                                else url_for("home"))
        flash("Invalid credentials.", "error")
        return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    if session.get("token"):
        try:
            api_post("/logout/")
        except Exception:
            pass
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))


@app.route("/home")
@login_required()
def home():
    return render_template("home.html",
                           name=session.get("name") or session.get("username", ""))


# ---------- browse / detail / purchase ----------

@app.route("/browse")
@login_required()
def browse():
    q = request.args.get("q", "").strip().lower()
    tickets = [_ticket_to_template(g) for g in _all_games()]
    if q:
        tickets = [t for t in tickets if q in t["name"].lower()]
    return render_template("browse.html", tickets=tickets, q=q)


@app.route("/ticket/<ticket_id>")
@login_required()
def ticket_detail(ticket_id):
    r = api_get(f"/lottery-games/{ticket_id}/")
    if not r.ok:
        flash("Ticket not found.", "error")
        return redirect(url_for("browse"))
    return render_template("ticket_detail.html",
                           ticket=_ticket_to_template(r.json()),
                           next_draw="Next scheduled draw")


@app.route("/purchase/<ticket_id>", methods=["GET", "POST"])
@login_required()
def purchase(ticket_id):
    r = api_get(f"/lottery-games/{ticket_id}/")
    if not r.ok:
        flash("Ticket not found.", "error")
        return redirect(url_for("browse"))
    ticket = _ticket_to_template(r.json())

    # fetch wallet balance for the form display
    balance = 0.0
    try:
        wb = api_get("/wallet/")
        if wb.ok:
            balance = float(wb.json().get("balance", "0"))
    except Exception:
        pass

    if request.method == "POST":
        try:
            quantity = int(request.form.get("quantity", "1"))
        except ValueError:
            quantity = 1
        if quantity < 1 or quantity > 10:
            flash("Quantity must be between 1 and 10.", "error")
            return redirect(url_for("purchase", ticket_id=ticket_id))

        payment = request.form.get("payment_method", "BK")
        pmap = {"paypal": "PP", "venmo": "VN", "bank": "BK", "wallet": "WL",
                "linked bank account": "BK"}
        payment_code = pmap.get(payment.lower(),
                                payment if payment in {"PP", "VN", "BK", "WL"} else "BK")

        items = []
        for i in range(1, quantity + 1):
            raw = request.form.get(f"numbers_{i}", "").strip()
            items.append({"lottery_type": ticket_id, "numbers": raw})

        resp = api_post("/purchase-tickets/", json={
            "payment_method": payment_code, "tickets": items,
        })
        if resp.status_code == 201:
            return redirect(url_for("order_confirmation", order_id=resp.json()["order_id"]))
        try:
            err = resp.json().get("error", "Purchase failed.")
        except Exception:
            err = "Purchase failed."
        flash(err, "error")
        return redirect(url_for("purchase", ticket_id=ticket_id))

    return render_template("purchase.html", ticket=ticket, wallet_balance=balance)


# ---------- orders ----------

def _build_order_view(payload, games):
    tickets = payload["tickets"]
    if not tickets:
        return None
    game_type = tickets[0]["lottery_type"]
    name = _name_for(game_type, games)
    price = _price_for(game_type, games)
    quantity = len(tickets)

    any_winner = any(t["winner"] for t in tickets)
    if any_winner:
        status = "winner"
    else:
        status = "pending_draw"

    total_winnings = sum(float(t["prize"]) for t in tickets)

    return {
        "order_id": payload["confirmation_number"],
        "raw_order_id": payload["order_id"],
        "ticket_id": game_type,
        "ticket_name": name,
        "quantity": quantity,
        "total_cost": price * quantity,
        "purchase_date": payload["created_at"],
        "payment_method": payload["payment_method"],
        "status": status,
        "total_winnings": total_winnings,
        "claimed": payload.get("claimed", False),
        "claimed_at": payload.get("claimed_at"),
        "tickets": [
            {
                "confirmation": t["ticket_number"],
                "numbers": [int(n) for n in (t["numbers"].split(",") if t["numbers"] else [])
                            if n.strip().lstrip("-").isdigit()],
                "prize": float(t["prize"]),
                "is_winner": t["winner"],
            }
            for t in tickets
        ],
    }


@app.route("/order/<order_id>")
@login_required()
def order_confirmation(order_id):
    r = api_get(f"/orders/{order_id}/")
    if not r.ok:
        flash("Order not found.", "error")
        return redirect(url_for("orders"))
    return render_template("order_confirmation.html",
                           order=_build_order_view(r.json(), _all_games()))


@app.route("/orders")
@login_required()
def orders():
    r = api_get("/user-orders/")
    if not r.ok:
        return render_template("orders.html", orders=[])
    games = _all_games()
    detailed = []
    for o in r.json():
        dr = api_get(f"/orders/{o['order_id']}/")
        if dr.ok:
            view = _build_order_view(dr.json(), games)
            if view:
                detailed.append(view)
    return render_template("orders.html", orders=detailed)


@app.route("/order_detail/<order_id>")
@login_required()
def order_detail(order_id):
    target = None
    if order_id.isdigit():
        r = api_get(f"/orders/{order_id}/")
        if r.ok:
            target = r.json()
    if target is None:
        r = api_get("/user-orders/")
        if r.ok:
            for o in r.json():
                if o["confirmation_number"] == order_id:
                    dr = api_get(f"/orders/{o['order_id']}/")
                    if dr.ok:
                        target = dr.json()
                        break
    if target is None:
        flash("Order not found.", "error")
        return redirect(url_for("orders"))
    return render_template("order_detail.html",
                           order=_build_order_view(target, _all_games()))


@app.route("/claim/<order_id>", methods=["POST"])
@login_required()
def claim(order_id):
    """Phase 3: claim is now persistent and credits to wallet."""
    # resolve confirmation_number -> raw id if needed
    raw_id = None
    if order_id.isdigit():
        raw_id = order_id
    else:
        r = api_get("/user-orders/")
        if r.ok:
            for o in r.json():
                if o["confirmation_number"] == order_id:
                    raw_id = str(o["order_id"])
                    break
    if raw_id is None:
        flash("Order not found.", "error")
        return redirect(url_for("orders"))

    resp = api_post(f"/orders/{raw_id}/claim/")
    if resp.ok:
        d = resp.json()
        flash(f"Prize claimed! ${d['amount_credited']} credited to your wallet "
              f"(balance now ${d['new_balance']}).", "success")
    else:
        try:
            err = resp.json().get("error", "Claim failed.")
        except Exception:
            err = "Claim failed."
        flash(err, "error")
    return redirect(url_for("order_detail", order_id=order_id))


# ---------- winning numbers ----------

@app.route("/winning_numbers")
@login_required()
def winning_numbers():
    r = api_get("/winning-numbers/")
    raw = r.json() if r.ok else []
    draws = [
        {
            "ticket_name": d["game"], "ticket_id": d["game_type"],
            "draw_date": d["draw_date"],
            "winning_numbers": [int(n) for n in d["winning_numbers"].split(",")
                                if n.strip().lstrip("-").isdigit()],
            "prize_amount": float(d["prize_amount"]),
        }
        for d in raw
    ]
    return render_template("winning_numbers.html", draws=draws)


# ---------- profile + wallet + spending limits ----------

@app.route("/profile")
@login_required()
def profile():
    r = api_get("/profile/")
    data = r.json() if r.ok else {}
    user = {
        "name": (f"{data.get('first_name','')} {data.get('last_name','')}".strip()
                 or data.get("username", "")),
        "first_name": data.get("first_name", ""),
        "last_name": data.get("last_name", ""),
        "email": data.get("email", ""),
        "address": data.get("home_address", ""),
        "phone": data.get("phone_number", ""),
        "role": "admin" if data.get("is_admin") else "customer",
        "wallet_balance": float(data.get("wallet_balance", "0")),
        "weekly_limit": float(data.get("weekly_spending_limit", "0")),
        "spent_this_week": float(data.get("spending_window_total", "0")),
    }
    return render_template("profile.html", user=user)


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required()
def profile_edit():
    if request.method == "POST":
        full_name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()

        if not all([full_name, email, address, phone]):
            flash("All fields are required.", "error")
            return redirect(url_for("profile_edit"))

        r = api_post("/profile/", json={
            "full_name": full_name,
            "email": email,
            "home_address": address,
            "phone_number": phone,
        })
        if r.ok:
            d = r.json()
            # update Flask session so nav reflects new name/email
            session["email"] = d.get("email", email)
            session["name"] = (f"{d.get('first_name','')} {d.get('last_name','')}".strip()
                               or d.get("username", ""))
            session["username"] = d.get("username", session.get("username"))
            flash("Profile updated.", "success")
            return redirect(url_for("profile"))

        try:
            err = r.json().get("error", "Update failed.")
        except Exception:
            err = "Update failed."
        flash(err, "error")
        return redirect(url_for("profile_edit"))

    r = api_get("/profile/")
    data = r.json() if r.ok else {}
    user = {
        "name": (f"{data.get('first_name','')} {data.get('last_name','')}".strip()
                 or data.get("username", "")),
        "email": data.get("email", ""),
        "address": data.get("home_address", ""),
        "phone": data.get("phone_number", ""),
    }
    return render_template("profile_edit.html", user=user)


@app.route("/wallet", methods=["GET", "POST"])
@login_required()
def wallet():
    if request.method == "POST":
        amt = request.form.get("amount", "0").strip()
        try:
            float(amt)
        except ValueError:
            flash("Invalid amount.", "error")
            return redirect(url_for("wallet"))
        r = api_post("/wallet/topup/", json={"amount": amt})
        if r.ok:
            flash(r.json().get("message", "Top-up successful."), "success")
        else:
            try:
                err = r.json().get("error", "Top-up failed.")
            except Exception:
                err = "Top-up failed."
            flash(err, "error")
        return redirect(url_for("wallet"))

    r = api_get("/profile/")
    data = r.json() if r.ok else {}
    return render_template("wallet.html",
                           balance=float(data.get("wallet_balance", "0")))


@app.route("/spending_limit", methods=["POST"])
@login_required()
def spending_limit():
    limit = request.form.get("limit", "0").strip()
    try:
        float(limit)
    except ValueError:
        flash("Invalid limit.", "error")
        return redirect(url_for("profile"))
    r = api_post("/spending-limit/", json={"limit": limit})
    if r.ok:
        flash(r.json().get("message", "Limit updated."), "success")
    else:
        flash("Could not update limit.", "error")
    return redirect(url_for("profile"))


# ---------- notifications ----------

@app.route("/notifications")
@login_required()
def notifications():
    r = api_get("/notifications/")
    items = r.json() if r.ok else []
    # silently mark all as read on view
    api_post("/notifications/mark-all-read/")
    return render_template("notifications.html", notifications=items)


# ---------- admin ----------

@app.route("/admin")
@login_required(role="admin")
def admin_dashboard():
    r = api_get("/admin-view/")
    if not r.ok:
        flash("Couldn't load admin stats.", "error")
        return redirect(url_for("home"))
    s = r.json()
    return render_template(
        "admin_dashboard.html",
        stats={"tickets_sold": s.get("total_tickets_sold", 0),
               "revenue": float(s.get("total_revenue", "0"))},
        total_users=s.get("total_users", 0),
        total_orders=s.get("total_orders", 0),
    )


@app.route("/admin/analytics")
@login_required(role="admin")
def admin_analytics():
    r = api_get("/admin-analytics/")
    if not r.ok:
        flash("Couldn't load analytics.", "error")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_analytics.html", data=r.json())


@app.route("/admin/tickets")
@login_required(role="admin")
def admin_tickets():
    return render_template("admin_tickets.html",
                           tickets=[_ticket_to_template(g) for g in _all_games()])


@app.route("/admin/tickets/add", methods=["GET", "POST"])
@login_required(role="admin")
def admin_add_ticket():
    if request.method == "POST":
        ticket_id = request.form.get("ticket_id", "").strip().upper()[:2]
        try:
            price = float(request.form.get("price", "0"))
            winning = float(request.form.get("winning_amount", "0"))
        except ValueError:
            flash("Invalid price or prize amount.", "error")
            return redirect(url_for("admin_add_ticket"))
        r = api_post("/admin-add-ticket/", json={
            "game_type": ticket_id, "ticket_price": str(price), "prize_amount": str(winning),
        })
        if r.status_code == 201:
            flash(f"Ticket {ticket_id} added.", "success")
            return redirect(url_for("admin_tickets"))
        flash(f"Add failed: {r.text[:120]}", "error")
        return redirect(url_for("admin_add_ticket"))
    return render_template("admin_ticket_form.html", action="Add", ticket=None)


@app.route("/admin/tickets/edit/<ticket_id>", methods=["GET", "POST"])
@login_required(role="admin")
def admin_edit_ticket(ticket_id):
    if request.method == "POST":
        try:
            price = float(request.form.get("price", "0"))
            winning = float(request.form.get("winning_amount", "0"))
        except ValueError:
            flash("Invalid price or prize amount.", "error")
            return redirect(url_for("admin_tickets"))
        r = api_put("/admin-update-ticket/", json={
            "game_type": ticket_id, "ticket_price": str(price), "prize_amount": str(winning),
        })
        if r.ok:
            flash(f"Ticket {ticket_id} updated.", "success")
        else:
            flash(f"Update failed: {r.text[:120]}", "error")
        return redirect(url_for("admin_tickets"))
    g = api_get(f"/lottery-games/{ticket_id}/")
    if not g.ok:
        flash("Ticket not found.", "error")
        return redirect(url_for("admin_tickets"))
    return render_template("admin_ticket_form.html", action="Edit",
                           ticket=_ticket_to_template(g.json()))


@app.route("/admin/tickets/remove/<ticket_id>", methods=["POST"])
@login_required(role="admin")
def admin_remove_ticket(ticket_id):
    r = api_post("/admin-remove-ticket/", json={"game_type": ticket_id})
    if r.ok:
        flash(f"Ticket {ticket_id} removed.", "success")
    else:
        flash(f"Remove failed: {r.text[:120]}", "error")
    return redirect(url_for("admin_tickets"))


@app.route("/admin/draw", methods=["GET", "POST"])
@login_required(role="admin")
def admin_draw():
    if request.method == "POST":
        ticket_id = request.form.get("ticket_id")
        forced = request.form.get("winning_numbers", "").strip()
        payload = {"game_type": ticket_id}
        if forced:
            payload["winning_numbers"] = forced
        r = api_post("/admin-run-draw/", json=payload)
        if r.ok:
            d = r.json()
            tag = " (forced)" if d.get("forced") else ""
            flash(f"Draw run{tag}: winning numbers {d.get('winning_numbers')}", "success")
        else:
            flash(f"Draw failed: {r.text[:120]}", "error")
        return redirect(url_for("admin_draw"))

    games = _all_games()
    wn = api_get("/winning-numbers/")
    by_game = {}
    if wn.ok:
        for d in wn.json():
            by_game.setdefault(d["game_type"], d)

    draws = []
    for g in games:
        gt = g["game_type"]
        latest = by_game.get(gt)
        draws.append({
            "ticket_id": gt, "ticket_name": g["name"],
            "draw_date": latest["draw_date"] if latest else "Pending",
            "winning_numbers": (
                [int(n) for n in latest["winning_numbers"].split(",")
                 if n.strip().lstrip("-").isdigit()] if latest else []
            ),
            "prize_amount": float(g["prize_amount"]),
        })
    return render_template("admin_draw.html", draws=draws)


@app.route("/admin/reset", methods=["POST"])
@login_required(role="admin")
def admin_reset():
    flash("Reset disabled in API mode. Re-run `python manage.py seed_lps` to reset data.", "info")
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
