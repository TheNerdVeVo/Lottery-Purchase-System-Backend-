# Lottery Purchase System (LPS)

**CS3365 – Team 9 – Phase 2 (Spring 2026)**

A web-based Lottery Purchase System for the Texas Lottery Commission, built with Flask.

## Team 9
- Maya Hattarki (mhattark@ttu.edu)
- Shadman Samir (ssamir@ttu.edu)
- Jelena Veselinovic (jveselin@ttu.edu)
- Chekwube Stanley Ononuju (cononuju@ttu.edu)
- Josue Isabel Jimenez (jim46965@ttu.edu)

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
python app.py

# 3. Open in browser
http://127.0.0.1:5000
```

## Demo Credentials

| Role     | Email           | Password   |
|----------|-----------------|------------|
| Admin    | admin@lps.gov   | admin123   |
| Customer | (register one)  | (your own) |

## Implemented Functionality

### Customer
- [x] Register / Log in / Log out
- [x] Browse all available lottery tickets
- [x] Search tickets by name
- [x] View ticket details (price, jackpot, prize structure, next draw)
- [x] Purchase 1–10 tickets per order (manual pick or auto-pick 5 numbers from 1–50)
- [x] Pay via PayPal, Venmo, or Bank Account
- [x] Receive electronic ticket with unique confirmation number
- [x] View order history with winner indicators
- [x] View order details with winning numbers highlighted
- [x] Claim prizes online (under $600) directly to payment method
- [x] Prizes ≥ $600 routed to in-person claiming center
- [x] View latest winning numbers across all ticket types
- [x] View profile information

### Admin
- [x] Separate admin dashboard
- [x] System status (tickets sold, revenue, customer count, order count)
- [x] Add new lottery tickets
- [x] Edit ticket name, price, prize amount
- [x] Remove (deactivate) tickets
- [x] Run new drawings to generate winning numbers
- [x] Reset demo data

### Compliance with Phase 1 spec
- [x] In-house auth (no third-party login)
- [x] No guest checkout
- [x] 50 numbers, pick 5
- [x] Same rules across all 4 default tickets
- [x] Weekly drawings
- [x] Winnings: 5/4/3/2/1 → 100%/20%/5%/1%/0%
- [x] Winning notification on Order History page

## Demo Video Script

Each team member presents one section:

### 1. Maya — Registration & Login (~1 min)
- Open app, register a new account ("Maya Test" / maya@example.com)
- Log out, log back in
- Show home dashboard tiles

### 2. Shadman — Browse, Search, Purchase (~2 min)
- Browse all 4 tickets
- Search "Mega" → filter results
- Click into Power Ball, view details
- Buy 3 tickets: 2 auto-pick + 1 manual (e.g. 7, 14, 22, 31, 49 to force a win for demo)
- Pay via PayPal
- Show electronic ticket confirmation

### 3. Jelena — Order History & Winnings (~1.5 min)
- View order history page
- Show order with "Winner" badge
- Open order detail; highlight matched numbers in gold
- Claim prize (under $600) → success message

### 4. Chekwube — Frontend & UX walkthrough (~1.5 min)
- Show responsive design (resize window)
- Walk through visual hierarchy: navbar, hero, ticket cards with color coding per ticket type
- Show winning numbers page
- Show profile page
- Demonstrate flash messages (try to register with existing email)

### 5. Josue — Admin Functionality (~2 min)
- Log out, log in as admin
- Show admin dashboard with live stats (revenue updated from earlier purchases)
- Manage Tickets → Add new ticket "Texas Cash 5" / $1.00 / $250,000
- Edit existing ticket price
- Run new draw for Power Ball → show updated winning numbers
- Log back in as customer, show how the prior order's status updated

## File Layout
```
lps/
├── app.py              # Flask application (all routes)
├── data.json           # Auto-generated on first run
├── requirements.txt
├── README.md
├── static/
│   └── css/style.css
└── templates/
    ├── base.html
    ├── login.html, register.html
    ├── home.html, browse.html, ticket_detail.html
    ├── purchase.html, order_confirmation.html
    ├── orders.html, order_detail.html
    ├── winning_numbers.html, profile.html
    ├── admin_dashboard.html, admin_tickets.html
    ├── admin_ticket_form.html, admin_draw.html
```
