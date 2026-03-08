import sqlite3
from config import DB_PATH


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id   INTEGER PRIMARY KEY,
            username  TEXT,
            full_name TEXT,
            joined_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS channels (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id    INTEGER,
            title       TEXT,
            link        TEXT UNIQUE,
            topic       TEXT,
            subscribers INTEGER,
            description TEXT,
            rating      REAL DEFAULT 5.0,
            piar_count  INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS deals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            from_channel INTEGER,
            to_channel   INTEGER,
            status       TEXT DEFAULT 'pending',
            created_at   TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_id    INTEGER,
            from_id    INTEGER,
            text       TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS reviews (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_id    INTEGER,
            from_id    INTEGER,
            stars      INTEGER,
            comment    TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


def fetchone(q, p=()):
    c = get_conn(); r = c.execute(q, p).fetchone(); c.close(); return r

def fetchall(q, p=()):
    c = get_conn(); r = c.execute(q, p).fetchall(); c.close(); return r

def execute(q, p=()):
    c = get_conn(); c.execute(q, p); c.commit(); c.close()

def execute_returning(q, p=()):
    c = get_conn(); cur = c.execute(q, p); c.commit(); lid = cur.lastrowid; c.close(); return lid


def upsert_user(user_id, username, full_name):
    execute("""
        INSERT INTO users(user_id,username,full_name) VALUES(?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,full_name=excluded.full_name
    """, (user_id, username, full_name))

def get_channel_by_owner(owner_id):
    return fetchone("SELECT * FROM channels WHERE owner_id=?", (owner_id,))

def get_channel_by_id(cid):
    return fetchone("SELECT * FROM channels WHERE id=?", (cid,))

def create_channel(owner_id, title, link, topic, subscribers, description):
    return execute_returning(
        "INSERT INTO channels(owner_id,title,link,topic,subscribers,description) VALUES(?,?,?,?,?,?)",
        (owner_id, title, link, topic, subscribers, description)
    )

def update_channel(cid, title, link, topic, subscribers, description):
    execute("UPDATE channels SET title=?,link=?,topic=?,subscribers=?,description=? WHERE id=?",
            (title, link, topic, subscribers, description, cid))

def search_channels(topic, min_s, max_s, exclude_owner):
    return fetchall("""
        SELECT * FROM channels
        WHERE topic=? AND subscribers BETWEEN ? AND ? AND owner_id!=?
        ORDER BY rating DESC, piar_count DESC LIMIT 20
    """, (topic, min_s, max_s, exclude_owner))

def get_top_channels(limit=10):
    return fetchall("SELECT * FROM channels ORDER BY rating DESC,piar_count DESC LIMIT ?", (limit,))

def create_deal(from_ch, to_ch):
    return execute_returning("INSERT INTO deals(from_channel,to_channel) VALUES(?,?)", (from_ch, to_ch))

def get_deal(did):
    return fetchone("SELECT * FROM deals WHERE id=?", (did,))

def activate_deal(did):
    execute("UPDATE deals SET status='active' WHERE id=?", (did,))

def decline_deal(did):
    execute("UPDATE deals SET status='declined' WHERE id=?", (did,))

def complete_deal(did):
    execute("UPDATE deals SET status='completed',completed_at=datetime('now') WHERE id=?", (did,))
    deal = get_deal(did)
    if deal:
        execute("UPDATE channels SET piar_count=piar_count+1 WHERE id=?", (deal[1],))
        execute("UPDATE channels SET piar_count=piar_count+1 WHERE id=?", (deal[2],))

def get_active_deal(ch1, ch2):
    return fetchone("""
        SELECT * FROM deals
        WHERE ((from_channel=? AND to_channel=?) OR (from_channel=? AND to_channel=?))
          AND status IN ('pending','active')
    """, (ch1, ch2, ch2, ch1))

def get_user_deals(channel_id):
    return fetchall("""
        SELECT d.*, cf.title,cf.link, ct.title,ct.link
        FROM deals d
        JOIN channels cf ON d.from_channel=cf.id
        JOIN channels ct ON d.to_channel=ct.id
        WHERE (d.from_channel=? OR d.to_channel=?) AND d.status!='declined'
        ORDER BY d.created_at DESC
    """, (channel_id, channel_id))

def add_message(deal_id, from_id, text):
    execute("INSERT INTO messages(deal_id,from_id,text) VALUES(?,?,?)", (deal_id, from_id, text))

def get_messages(deal_id):
    return fetchall("SELECT * FROM messages WHERE deal_id=? ORDER BY created_at", (deal_id,))

def add_review(deal_id, from_id, stars, comment):
    execute("INSERT INTO reviews(deal_id,from_id,stars,comment) VALUES(?,?,?,?)",
            (deal_id, from_id, stars, comment))
    deal = get_deal(did=deal_id)
    if not deal: return
    from_ch = get_channel_by_id(deal[1])
    reviewed_ch_id = deal[2] if (from_ch and from_ch[1] == from_id) else deal[1]
    avg = fetchone("""
        SELECT AVG(r.stars) FROM reviews r JOIN deals d ON r.deal_id=d.id
        WHERE d.from_channel=? OR d.to_channel=?
    """, (reviewed_ch_id, reviewed_ch_id))
    if avg and avg[0]:
        execute("UPDATE channels SET rating=? WHERE id=?", (round(avg[0], 1), reviewed_ch_id))
