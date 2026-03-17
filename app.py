from flask import Flask, render_template, request, redirect, session
import sqlite3
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "fin-partners-secret"


def db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# LOGIN
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = db()

        user = conn.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email,password)
        ).fetchone()

        conn.close()

        if user:

            session["user_id"] = user["id"]

            return redirect("/dashboard")

    return render_template("login.html")


# REGISTER
@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = db()

        conn.execute(
        "INSERT INTO users(email,password,balance) VALUES (?,?,0)",
        (email,password)
        )

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


# LOGOUT
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# DASHBOARD
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = db()

    clicks = conn.execute(
    "SELECT COUNT(*) FROM clicks WHERE user_id=?",
    (user_id,)
    ).fetchone()[0]

    leads = conn.execute(
    "SELECT COUNT(*) FROM conversions WHERE user_id=?",
    (user_id,)
    ).fetchone()[0]

    money = conn.execute(
    "SELECT SUM(payout) FROM conversions WHERE user_id=?",
    (user_id,)
    ).fetchone()[0]

    if not money:
        money = 0

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

    conn.close()

    return render_template(
    "dashboard.html",
    clicks=clicks,
    leads=leads,
    money=money,
    leads_table=leads_table
    )


# OFFERS
@app.route("/offers")
def offers():

    conn = db()

    offers = conn.execute(
    "SELECT * FROM offers"
    ).fetchall()

    conn.close()

    return render_template("offers.html",offers=offers)


# PARTNER LINKS
@app.route("/flows")
def flows():

    if "user_id" not in session:
        return redirect("/login")

    conn = db()

    offers = conn.execute(
    "SELECT * FROM offers"
    ).fetchall()

    conn.close()

    return render_template(
    "flows.html",
    offers=offers,
    user_id=session["user_id"]
    )


# PUBLIC TRACKING LINK
@app.route("/go/<offer_id>")
def go(offer_id):

    ref = request.args.get("ref")

    click_id = str(uuid.uuid4())

    conn = db()

    offer = conn.execute(
    "SELECT * FROM offers WHERE id=?",
    (offer_id,)
    ).fetchone()

    conn.execute(
    """
    INSERT INTO clicks(click_id,user_id,offer_id,created_at)
    VALUES(?,?,?,?)
    """,
    (click_id,ref,offer_id,datetime.now())
    )

    conn.commit()
    conn.close()

    redirect_url = offer["url"] + "&sub1=" + click_id

    return redirect(redirect_url)


# TEST CLICK
@app.route("/click/<offer_id>")
def click(offer_id):

    user_id = session.get("user_id")

    click_id = str(uuid.uuid4())

    conn = db()

    offer = conn.execute(
    "SELECT * FROM offers WHERE id=?",
    (offer_id,)
    ).fetchone()

    conn.execute(
    """
    INSERT INTO clicks(click_id,user_id,offer_id,created_at)
    VALUES(?,?,?,?)
    """,
    (click_id,user_id,offer_id,datetime.now())
    )

    conn.commit()
    conn.close()

    redirect_url = offer["url"] + "&sub1=" + click_id

    return redirect(redirect_url)


# POSTBACK
@app.route("/postback")
def postback():

    click_id = request.args.get("sub1")

    conn = db()

    click = conn.execute(
    "SELECT * FROM clicks WHERE click_id=?",
    (click_id,)
    ).fetchone()

    if not click:
        return "click not found"

    payout = conn.execute(
    "SELECT payout FROM offers WHERE id=?",
    (click["offer_id"],)
    ).fetchone()[0]

    conn.execute(
    """
    INSERT INTO conversions(click_id,user_id,offer_id,status,payout,created_at)
    VALUES(?,?,?,?,?,?)
    """,
    (click_id,click["user_id"],click["offer_id"],"approved",payout,datetime.now())
    )

    conn.execute(
    "UPDATE users SET balance = balance + ? WHERE id=?",
    (payout,click["user_id"])
    )

    conn.commit()
    conn.close()

    return "ok"


# LEADS PAGE
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
    """,
    (session["user_id"],)
    ).fetchall()

    conn.close()

    return render_template("leads.html",leads=leads)


# PAYOUTS
@app.route("/payouts",methods=["GET","POST"])
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
        SET payout_method=?,payout_details=?
        WHERE id=?
        """,
        (method,details,session["user_id"])
        )

        conn.commit()

    user = conn.execute(
    "SELECT * FROM users WHERE id=?",
    (session["user_id"],)
    ).fetchone()

    conn.close()

    return render_template("payouts.html",user=user)

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
