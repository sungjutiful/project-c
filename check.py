import sqlite3
c = sqlite3.connect('reviews.db')

# status별로 몇 건인지 전부 보기
rows = c.execute("SELECT status, COUNT(*) FROM reviews GROUP BY status").fetchall()
print("=== status별 건수 ===")
for status, cnt in rows:
    print(f"  {status}: {cnt}건")

# 전체 건수
total = c.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
print(f"=== 전체: {total}건 ===")
c.close()