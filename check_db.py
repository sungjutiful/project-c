import sqlite3

conn = sqlite3.connect('reviews.db')
cur = conn.cursor()

# 1. 테이블 목록 확인
print("=== 테이블 목록 ===")
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    print(t[0])

# 2. reviews 테이블 컬럼 구조 확인
print("\n=== reviews 컬럼 구조 ===")
cols = cur.execute("PRAGMA table_info(reviews)").fetchall()
for col in cols:
    print(f"{col[1]:20} {col[2]}")   # 컬럼명, 타입

# 3. 데이터 1건 미리보기
print("\n=== 데이터 샘플 1건 ===")
row = cur.execute("SELECT * FROM reviews LIMIT 1").fetchone()
print(row)

conn.close()