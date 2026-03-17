from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "fin-partners-secret"


def db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT,
        balance INTEGER DEFAULT 0,
        payout_method TEXT DEFAULT '',
        payout_details TEXT DEFAULT ''
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS offers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        payout INTEGER,
        url TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS clicks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        click_id TEXT UNIQUE,
        user_id INTEGER,
        offer_id INTEGER,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS conversions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        click_id TEXT,
        user_id INTEGER,
        offer_id INTEGER,
        status TEXT,
        payout INTEGER,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


@app.route("/")
def home():
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"].strip()

        conn = db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            return redirect("/dashboard")

        return redirect("/login")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"].strip()

        conn = db()
        try:
            conn.execute(
                "INSERT INTO users(email,password,balance,payout_method,payout_details) VALUES (?,?,0,'','')",
                (email, password)
            )
            conn.commit()
        except:
            conn.close()
            return redirect("/register")

        conn.close()
        return redirect("/login")

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    conn = db()

    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    clicks = conn.execute(
        "SELECT COUNT(*) AS total FROM clicks WHERE user_id=?",
        (user_id,)
    ).fetchone()["total"]

    leads = conn.execute(
        "SELECT COUNT(*) AS total FROM conversions WHERE user_id=?",
        (user_id,)
    ).fetchone()["total"]

    money = conn.execute(
        "SELECT COALESCE(SUM(payout),0) AS total FROM conversions WHERE user_id=?",
        (user_id,)
    ).fetchone()["total"]

    paid = 0

    leads_table = conn.execute(
        """
        SELECT conversions.*, offers.name
        FROM conversions
        LEFT JOIN offers
        ON conversions.offer_id = offers.id
        WHERE conversions.user_id=?
        ORDER BY conversions.id DESC
        LIMIT 10
        """,
        (user_id,)
    ).fetchall()

    today = datetime.now().date()
    labels = []
    clicks_chart = []
    revenue_chart = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        next_day = day + timedelta(days=1)

        labels.append(day.strftime("%d.%m"))

        click_count = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM clicks
            WHERE user_id=? AND created_at >= ? AND created_at < ?
            """,
            (user_id, f"{day} 00:00:00", f"{next_day} 00:00:00")
        ).fetchone()["total"]

        revenue_sum = conn.execute(
            """
            SELECT COALESCE(SUM(payout),0) AS total
            FROM conversions
            WHERE user_id=? AND created_at >= ? AND created_at < ?
            """,
            (user_id, f"{day} 00:00:00", f"{next_day} 00:00:00")
        ).fetchone()["total"]

        clicks_chart.append(click_count)
        revenue_chart.append(revenue_sum)

    conn.close()

    return render_template(
        "dashboard.html",
        user=user,
        clicks=clicks,
        leads=leads,
        money=money,
        paid=paid,
        leads_table=leads_table,
        chart_labels=labels,
        clicks_chart=clicks_chart,
        revenue_chart=revenue_chart
    )


@app.route("/offers")
def offers():
    if "user_id" not in session:
        return redirect("/login")

    conn = db()
    offers = conn.execute("SELECT * FROM offers").fetchall()
    conn.close()

    return render_template("offers.html", offers=offers)


@app.route("/flows")
def flows():
    if "user_id" not in session:
        return redirect("/login")

    conn = db()
    offers = conn.execute("SELECT * FROM offers").fetchall()
    conn.close()

    return render_template(
        "flows.html",
        offers=offers,
        user_id=session["user_id"]
    )


@app.route("/go/<offer_id>")
def go(offer_id):
    ref = request.args.get("ref")
    click_id = str(uuid.uuid4())

    conn = db()

    offer = conn.execute(
        "SELECT * FROM offers WHERE id=?",
        (offer_id,)
    ).fetchone()

    if not offer:
        conn.close()
        return "offer not found"

    conn.execute(
        """
        INSERT INTO clicks(click_id,user_id,offer_id,created_at)
        VALUES(?,?,?,?)
        """,
        (click_id, ref, offer_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

    conn.commit()
    conn.close()

    redirect_url = offer["url"] + "&sub1=" + click_id
    return redirect(redirect_url)


@app.route("/click/<offer_id>")
def click(offer_id):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    click_id = str(uuid.uuid4())

    conn = db()

    offer = conn.execute(
        "SELECT * FROM offers WHERE id=?",
        (offer_id,)
    ).fetchone()

    if not offer:
        conn.close()
        return "offer not found"

    conn.execute(
        """
        INSERT INTO clicks(click_id,user_id,offer_id,created_at)
        VALUES(?,?,?,?)
        """,
        (click_id, user_id, offer_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

    conn.commit()
    conn.close()

    redirect_url = offer["url"] + "&sub1=" + click_id
    return redirect(redirect_url)


@app.route("/postback")
def postback():
    click_id = request.args.get("sub1")

    conn = db()

    click = conn.execute(
        "SELECT * FROM clicks WHERE click_id=?",
        (click_id,)
    ).fetchone()

    if not click:
        conn.close()
        return "click not found"

    payout = conn.execute(
        "SELECT payout FROM offers WHERE id=?",
        (click["offer_id"],)
    ).fetchone()["payout"]

    exists = conn.execute(
        "SELECT id FROM conversions WHERE click_id=?",
        (click_id,)
    ).fetchone()

    if exists:
        conn.close()
        return "duplicate"

    conn.execute(
        """
        INSERT INTO conversions(click_id,user_id,offer_id,status,payout,created_at)
        VALUES(?,?,?,?,?,?)
        """,
        (
            click_id,
            click["user_id"],
            click["offer_id"],
            "approved",
            payout,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    conn.execute(
        "UPDATE users SET balance = balance + ? WHERE id=?",
        (payout, click["user_id"])
    )

    conn.commit()
    conn.close()

    return "ok"


@app.route("/leads")
def leads():
    if "user_id" not in session:
        return redirect("/login")

    conn = db()
    leads = conn.execute(
        """
        SELECT conversions.*, offers.name
        FROM conversions
        LEFT JOIN offers
        ON conversions.offer_id = offers.id
        WHERE conversions.user_id=?
        ORDER BY conversions.id DESC
        """,
        (session["user_id"],)
    ).fetchall()
    conn.close()

    return render_template("leads.html", leads=leads)


@app.route("/payouts", methods=["GET", "POST"])
def payouts():
    if "user_id" not in session:
        return redirect("/login")

    conn = db()

    if request.method == "POST":
        method = request.form["method"]
        details = request.form["details"]

        conn.execute(
            """
            UPDATE users
            SET payout_method=?, payout_details=?
            WHERE id=?
            """,
            (method, details, session["user_id"])
        )
        conn.commit()

    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    conn.close()

    return render_template("payouts.html", user=user)


@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")

    conn = db()
    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    return render_template("profile.html", user=user)
