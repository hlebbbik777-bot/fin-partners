import sqlite3

conn = sqlite3.connect("database.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
email TEXT UNIQUE,
password TEXT,
balance INTEGER DEFAULT 0,
payout_method TEXT,
payout_details TEXT
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

c.execute("""
INSERT INTO offers(name,payout,url)
VALUES(
'ВТБ дебетовая карта',
1500,
'https://u-cpa.ru/offer/rs/2kktqbn0vhg02/38ynycdkfpvoc/?partner=230941&erid=Kra23hiMc&platform_id=31136'
)
""")

conn.commit()
conn.close()

print("DATABASE READY")
