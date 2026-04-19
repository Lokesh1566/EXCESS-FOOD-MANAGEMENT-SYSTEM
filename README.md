# FoodRescue - Excess Food Management System

A full-stack web platform that connects surplus food donors (restaurants, caterers, individuals) with NGOs and communities who need it. Reducing food waste, one donation at a time.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=flat-square&logo=bootstrap&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)

---

## the problem

~1.3 billion tons of food is wasted globally every year. Restaurants throw away leftovers, caterers dump excess from cancelled events, and grocery stores discard perfectly edible produce. Meanwhile, millions go hungry. This platform bridges that gap.

## what it does

- **Donors** (restaurants, caterers, individuals) list surplus food with quantity, pickup address, and expiry time
- **Receivers** (NGOs, shelters, community kitchens) browse available donations nearby and claim them
- Real time availability tracking expired listings auto-hide
- City and food type filtering for quick discovery
- Contact info exchange on claim for pickup coordination
- REST API endpoints for future mobile app integration

## quick start

```bash
git clone https://github.com/Lokesh1566/EXCESS-FOOD-MANAGEMENT-SYSTEM.git
cd EXCESS-FOOD-MANAGEMENT-SYSTEM
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

The app seeds demo data on first run 4 users and 5 donations so you can explore immediately.

**Demo accounts:**
| Role | Email | Password |
|------|-------|----------|
| Donor | ravi@example.com | password123 |
| Donor | priya@example.com | password123 |
| NGO/Receiver | ngo@example.com | password123 |
| NGO/Receiver | help@example.com | password123 |

## project structure

```
EXCESS-FOOD-MANAGEMENT-SYSTEM/
├── app.py                    # main flask application (routes, models, auth)
├── requirements.txt
├── Dockerfile
├── templates/
│   ├── base.html             # layout with navbar & footer
│   ├── index.html            # landing page with stats & recent donations
│   ├── login.html
│   ├── register.html
│   ├── create_donation.html  # form for listing surplus food
│   ├── browse.html           # browse & filter available donations
│   ├── view_donation.html    # donation detail + claim button
│   ├── dashboard_donor.html  # donor's donation management
│   ├── dashboard_receiver.html # receiver's available & claimed
│   └── profile.html          # edit user profile
├── static/
│   └── css/style.css
├── tests/
└── README.md
```

## features

**For donors:**
- List surplus food with type, quantity, description, and pickup details
- Set expiry window (2h to 48h) listings auto-expire
- Track which NGO claimed your donation
- Manage and remove listings from dashboard

**For receivers (NGOs):**
- Browse all available donations with city and food-type filters
- Claim donations with one click
- View donor contact info for pickup coordination
- Track claimed donation history

**System:**
- Role based authentication (donor vs receiver)
- Password hashing with Werkzeug
- SQLite database (zero config, works out of the box)
- Responsive Bootstrap 5 UI
- REST API at `/api/donations` and `/api/stats`
- Demo data seeding on first run

## API endpoints

```
GET  /api/donations  → list all available donations (JSON)
GET  /api/stats      → platform statistics (JSON)
```

## tech stack

- **Backend:** Flask, SQLite, Werkzeug
- **Frontend:** Jinja2 templates, Bootstrap 5, Bootstrap Icons
- **Auth:** Session-based with password hashing
- **Deployment:** Docker ready

## future improvements

- [ ] Google Maps integration for pickup locations
- [ ] Push notifications when new donations match receiver's city
- [ ] Image upload for food listings
- [ ] Rating system for donors and receivers
- [ ] Analytics dashboard for platform admins
- [ ] Migrate to PostgreSQL for production
- [ ] Mobile app (React Native) using the REST API

---

**Lokesh Reddy Elluri** — MS Data Science, Indiana University Bloomington
[LinkedIn](https://linkedin.com/in/lokesh-reddy-elluri-a77a7b201) · [Email](mailto:redfylokesh@gmail.com)
