"""
storage.py
DB 생성 · 저장 · 조회 공용 함수. B~E는 이 파일의 함수만 가져다 쓰고,
DB를 직접 만지지 않는다 (규칙).

reviews 테이블 1개 + extractions 테이블 1개로 구성.
raw로 들어온 리뷰는 status='raw', clean을 통과하면 status='clean'으로 표시된다.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "reviews.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT,
            rating INTEGER,
            review_date TEXT,
            text TEXT NOT NULL,
            text_clean TEXT,
            status TEXT DEFAULT 'raw',
            sentiment TEXT,
            score REAL,
            analyzed_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS extractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT (datetime('now')),
            target TEXT,
            pos_keywords TEXT,
            neg_keywords TEXT,
            summary TEXT,
            suggestions TEXT
        )
    """)
    conn.commit()
    conn.close()


# ── 저장 ──────────────────────────────

def text_exists(text: str) -> bool:
    """import 단계 중복 체크용 (raw 기준)."""
    conn = get_conn()
    row = conn.execute("SELECT id FROM reviews WHERE text = ?", (text,)).fetchone()
    conn.close()
    return row is not None


def insert_review(product, rating, review_date, text):
    conn = get_conn()
    conn.execute(
        "INSERT INTO reviews (product, rating, review_date, text, status) VALUES (?, ?, ?, ?, 'raw')",
        (product, rating, review_date, text),
    )
    conn.commit()
    conn.close()


def mark_cleaned(review_id, text_clean, rating=None, review_date=None):
    conn = get_conn()
    conn.execute(
        "UPDATE reviews SET text_clean = ?, status = 'clean', rating = COALESCE(?, rating), "
        "review_date = COALESCE(?, review_date) WHERE id = ?",
        (text_clean, rating, review_date, review_id),
    )
    conn.commit()
    conn.close()


def update_sentiment(review_id, sentiment, score):
    conn = get_conn()
    conn.execute(
        "UPDATE reviews SET sentiment = ?, score = ?, analyzed_at = datetime('now') WHERE id = ?",
        (sentiment, score, review_id),
    )
    conn.commit()
    conn.close()


def insert_extraction(target, pos_keywords, neg_keywords, summary, suggestions):
    conn = get_conn()
    conn.execute(
        "INSERT INTO extractions (target, pos_keywords, neg_keywords, summary, suggestions) "
        "VALUES (?, ?, ?, ?, ?)",
        (target, pos_keywords, neg_keywords, summary, suggestions),
    )
    conn.commit()
    conn.close()


# ── 조회 ──────────────────────────────

def get_all_reviews(status=None):
    conn = get_conn()
    if status:
        rows = conn.execute("SELECT * FROM reviews WHERE status = ?", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM reviews").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unanalyzed(limit=None):
    conn = get_conn()
    query = "SELECT * FROM reviews WHERE status = 'clean' AND sentiment IS NULL"
    if limit:
        query += f" LIMIT {int(limit)}"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_review_by_id(review_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def query_reviews(sentiment=None, rating=None, date_from=None, date_to=None, sort=None):
    conn = get_conn()
    query = "SELECT * FROM reviews WHERE status = 'clean'"
    params = []
    if sentiment:
        query += " AND sentiment = ?"
        params.append(sentiment)
    if rating:
        query += " AND rating = ?"
        params.append(rating)
    if date_from:
        query += " AND review_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND review_date <= ?"
        params.append(date_to)
    if sort == "rating":
        query += " ORDER BY rating DESC"
    else:
        query += " ORDER BY review_date"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_extraction():
    conn = get_conn()
    row = conn.execute("SELECT * FROM extractions ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None
