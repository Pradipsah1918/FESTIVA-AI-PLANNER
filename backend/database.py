from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'festiva.db'


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_cursor():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db_cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS vendor_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                category TEXT NOT NULL,
                priority INTEGER NOT NULL,
                avg_cost_share REAL NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                category TEXT NOT NULL,
                event_types TEXT NOT NULL,
                base_price INTEGER NOT NULL,
                rating REAL NOT NULL,
                tags TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                event_type TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS generated_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                budget INTEGER NOT NULL,
                city TEXT NOT NULL,
                preferences TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def seed_db() -> None:
    vendor_category_rows = [
        ('wedding', 'Venue', 1, 0.27),
        ('wedding', 'Catering', 2, 0.22),
        ('wedding', 'Decor', 3, 0.14),
        ('wedding', 'Photography', 4, 0.10),
        ('wedding', 'Entertainment', 5, 0.08),
        ('wedding', 'Beauty & Styling', 6, 0.06),
        ('wedding', 'Invitations', 7, 0.03),
        ('wedding', 'Logistics', 8, 0.10),
        ('corporate', 'Venue', 1, 0.24),
        ('corporate', 'Catering', 2, 0.18),
        ('corporate', 'AV & Production', 3, 0.20),
        ('corporate', 'Branding', 4, 0.08),
        ('corporate', 'Speaker & Talent', 5, 0.12),
        ('corporate', 'Registration', 6, 0.05),
        ('corporate', 'Logistics', 7, 0.13),
        ('birthday', 'Venue', 1, 0.20),
        ('birthday', 'Food & Cake', 2, 0.25),
        ('birthday', 'Decor', 3, 0.15),
        ('birthday', 'Entertainment', 4, 0.12),
        ('birthday', 'Photography', 5, 0.08),
        ('birthday', 'Return Gifts', 6, 0.07),
        ('birthday', 'Invitations', 7, 0.03),
        ('birthday', 'Logistics', 8, 0.10),
    ]

    vendor_rows = [
        ('Royal Orchid Banquets', 'Bangalore', 'Venue', 'wedding,corporate', 280000, 4.7, 'luxury,indoor,parking'),
        ('Gardenia Greens', 'Bangalore', 'Venue', 'wedding,birthday', 180000, 4.5, 'outdoor,garden,photogenic'),
        ('The Glasshouse Hub', 'Bangalore', 'Venue', 'corporate,birthday', 120000, 4.4, 'modern,central,av-ready'),
        ('Spice Route Catering', 'Bangalore', 'Catering', 'wedding,corporate,birthday', 220000, 4.8, 'veg,non-veg,premium'),
        ('Urban Feast Co.', 'Bangalore', 'Food & Cake', 'birthday', 90000, 4.4, 'buffet,cake,fast-service'),
        ('Urban Feast Co.', 'Bangalore', 'Catering', 'corporate', 90000, 4.4, 'buffet,live-counters,fast-service'),
        ('Petal & Pearl Decor', 'Bangalore', 'Decor', 'wedding,birthday', 140000, 4.7, 'floral,pastel,stage-design'),
        ('StageCraft Productions', 'Bangalore', 'AV & Production', 'corporate', 160000, 4.6, 'led-wall,lights,sound'),
        ('Memories by Mira', 'Bangalore', 'Photography', 'wedding,birthday', 85000, 4.9, 'candid,cinematic,reels'),
        ('EchoLive Entertainment', 'Bangalore', 'Entertainment', 'wedding,corporate,birthday', 70000, 4.5, 'dj,live-band,emcee'),
        ('BrideGlow Studio', 'Bangalore', 'Beauty & Styling', 'wedding', 60000, 4.6, 'bridal,trial,team'),
        ('BrandMint Creative', 'Bangalore', 'Branding', 'corporate', 45000, 4.3, 'signage,collateral,branding'),
        ('SwiftMove Logistics', 'Bangalore', 'Logistics', 'wedding,corporate,birthday', 50000, 4.4, 'transport,coordination,guest-helpdesk'),
        ('GiftNest Favors', 'Bangalore', 'Return Gifts', 'birthday,wedding', 30000, 4.2, 'custom,gifting,budget'),
        ('InviteInk', 'Bangalore', 'Invitations', 'wedding,birthday', 20000, 4.1, 'digital,print,custom-illustration'),
        ('Summit Speakers Bureau', 'Bangalore', 'Speaker & Talent', 'corporate', 125000, 4.5, 'keynote,host,moderator'),
        ('CheckIn Flow', 'Bangalore', 'Registration', 'corporate', 35000, 4.2, 'onsite,kiosk,badges'),
        ('Pastel Party Lab', 'Bangalore', 'Decor', 'birthday', 50000, 4.4, 'kids-theme,balloons,photo-booth')
    ]

    docs = [
        ('Wedding planning timeline', 'wedding', 'Start 6-8 months out by fixing budget, guest count, venue shortlist, and family priorities. In the next 4-6 months, lock venue, catering, decor, photography, makeup, and guest stay logistics. In the final 8 weeks, finalize invitations, outfits, rehearsals, transport plans, and payment milestones. During event week, run a minute-by-minute wedding-day schedule with vendor call sheet and emergency buffer.', 'Internal event playbook'),
        ('Corporate event checklist', 'corporate', 'Define event objective, audience, KPIs, date flexibility, and stakeholder roles first. Confirm venue and AV requirements early, then build a speaker run-of-show, registration workflow, branding assets, food plan, and contingency for technical delays. Post-event, capture leads, feedback, media assets, and budget variance.', 'Internal event playbook'),
        ('Birthday event guide', 'birthday', 'Birthday planning starts with the age group, guest count, theme, and indoor or outdoor preference. Allocate early budget to venue, food, cake, decor, and entertainment. Reserve extra buffer for last-minute add-ons like return gifts, extra seating, weather backup, and activity materials.', 'Internal event playbook'),
        ('Vendor selection rules', 'general', 'Choose vendors using a balanced scorecard: category fit, city proximity, event-type experience, rating, price-to-budget fit, and tags matching user preferences. Keep one premium, one balanced, and one value option whenever possible.', 'Internal ops guide')
    ]

    with db_cursor() as cur:
        cur.execute('SELECT COUNT(*) AS c FROM vendor_categories')
        if cur.fetchone()['c'] == 0:
            cur.executemany(
                'INSERT INTO vendor_categories (event_type, category, priority, avg_cost_share) VALUES (?, ?, ?, ?)',
                vendor_category_rows,
            )

        cur.execute('SELECT COUNT(*) AS c FROM vendors')
        if cur.fetchone()['c'] == 0:
            cur.executemany(
                'INSERT INTO vendors (name, city, category, event_types, base_price, rating, tags) VALUES (?, ?, ?, ?, ?, ?, ?)',
                vendor_rows,
            )

        cur.execute('SELECT COUNT(*) AS c FROM knowledge_docs')
        if cur.fetchone()['c'] == 0:
            cur.executemany(
                'INSERT INTO knowledge_docs (title, event_type, content, source) VALUES (?, ?, ?, ?)',
                docs,
            )
