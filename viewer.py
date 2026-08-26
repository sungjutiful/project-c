"""
viewer.py — D 담당
list:  필터(감정·별점·기간) + 정렬 + 페이지네이션 (Day 2)
show:  리뷰 1건 상세 — 원문 + 분석 결과 (Day 2)
stats: 전체 통계 요약 (Day 3)
export: CSV · 엑셀 · JSONL 내보내기 (Day 3)
"""

import json
import logging
import os
from datetime import datetime

import pandas as pd
import storage

logger = logging.getLogger("review_dashboard")

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def _stars(rating):
    """별점 5 → '★★★★☆' 식 표기. 없거나 숫자가 아니면 '-'."""
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return "-"
    if rating <= 0:
        return "-"
    rating = min(5, rating)
    return "★" * rating + "☆" * (5 - rating)


def _rating_int(value):
    """별점을 int로. 숫자가 아니면 None (raw 값이 섞여 있어도 죽지 않게)."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _sentiment(row):
    """감정+점수 표기. 점수가 비어 있어도 죽지 않게."""
    label = row.get("sentiment")
    if not label:
        return "미분석"
    try:
        return f"{label} ({float(row.get('score')):.2f})"
    except (TypeError, ValueError):
        return f"{label} (점수 없음)"


def _truncate(text, width=30):
    text = " ".join((text or "").split())
    return text if len(text) <= width else text[: width - 3] + "..."


def cmd_list(args):
    """list: 필터(감정·별점·기간) + 정렬 + 페이지네이션 (Day 2).
    storage.query_reviews가 clean 통과 행 전체를 돌려주므로
    페이지네이션은 여기서 슬라이스로 한다."""
    rows = storage.query_reviews(
        sentiment=args.sentiment,
        rating=args.rating,
        date_from=args.date_from,
        date_to=args.date_to,
        sort=args.sort,
    )
    total = len(rows)
    pages = max(1, (total + args.size - 1) // args.size)
    page_rows = rows[(args.page - 1) * args.size : args.page * args.size]

    filters = []
    if args.sentiment:
        filters.append(f"감정: {args.sentiment}")
    if args.rating is not None:
        filters.append(f"별점: {args.rating}")
    if args.date_from or args.date_to:
        filters.append(f"기간: {args.date_from or '...'} ~ {args.date_to or '...'}")
    label = ", ".join(filters) if filters else "전체"

    print(f"=== 리뷰 목록 ({label}, {args.page}/{pages} 페이지, 총 {total}건) ===")
    if not page_rows:
        logger.warning("list 조회 결과 0건 — 필터 조건을 확인하세요")
        print("[조건에 맞는 리뷰가 없습니다]")
        return
    for r in page_rows:
        date = r.get("review_date") or "-"
        print(
            f"[{r['id']}] {_stars(r.get('rating'))} | {date} | "
            f"{_truncate(r.get('text'))} | {_sentiment(r)}"
        )
    logger.info("list %d/%d 페이지 %d건 출력", args.page, pages, len(page_rows))


def cmd_show(args):
    """show: 리뷰 1건 상세 — 원문 + 분석 결과 (Day 2)."""
    row = storage.get_review_by_id(args.id)
    if row is None:
        logger.error("ID=%s 리뷰를 찾을 수 없습니다", args.id)
        return

    print(f"=== 리뷰 상세 (ID: {row['id']}) ===")
    print(f"제품명 : {row.get('product') or '-'}")
    rating_line = f"별점   : {_stars(row.get('rating'))}"
    try:
        rv = int(row.get("rating"))
        if rv:
            rating_line += f" ({rv}/5)"
    except (TypeError, ValueError):
        pass
    print(rating_line)
    print(f"작성일 : {row.get('review_date') or '-'}")
    print(f"상태   : {row.get('status')}")
    if row.get("sentiment"):
        print(f"감정 분석: {_sentiment(row)} | 분석 시각: {row.get('analyzed_at') or '-'}")
    else:
        print("감정 분석: 미분석")
    print("[원문]")
    print(row.get("text") or "")
    logger.info("show ID=%s 출력", row["id"])


def cmd_stats(args):
    """stats: 전체 통계 요약 (Day 3). 과제 예시 형식 그대로."""
    rows = storage.get_all_reviews()
    total = len(rows)
    if total == 0:
        logger.warning("stats: 저장된 리뷰가 없습니다 — import부터 실행하세요")
        print("[저장된 리뷰가 없습니다]")
        return

    analyzed = [r for r in rows if r.get("sentiment")]
    n_analyzed = len(analyzed)

    def pct(part, whole):
        return f"{part / whole * 100:.1f}%" if whole else "0.0%"

    print("=== 리뷰 분석 통계 ===")
    print(f"총 리뷰 수: {total}건")
    print(f"분석 완료: {n_analyzed}건 ({pct(n_analyzed, total)})")

    print("\n[감정 분포]")
    for label, key in (("긍정", "positive"), ("중립", "neutral"), ("부정", "negative")):
        n = sum(1 for r in analyzed if r["sentiment"] == key)
        print(f"- {label}: {n}건 ({pct(n, n_analyzed)})")

    print("\n[별점 분포]")
    for star in range(5, 0, -1):
        n = sum(1 for r in rows if _rating_int(r.get("rating")) == star)
        print(f"- {'★' * star}{'☆' * (5 - star)}: {n}건 ({pct(n, total)})")

    ratings = [v for v in (_rating_int(r.get("rating")) for r in rows) if v is not None and 1 <= v <= 5]
    scores = [float(r["score"]) for r in analyzed if r.get("score") is not None]
    print(f"\n평균 별점: {sum(ratings) / len(ratings):.2f}" if ratings else "\n평균 별점: -")
    print(f"평균 감정 점수: {sum(scores) / len(scores):.2f}" if scores else "평균 감정 점수: -")
    logger.info("stats: 총 %d건, 분석 %d건 집계", total, n_analyzed)


EXPORT_COLUMNS = ["id", "product", "rating", "review_date", "text", "text_clean",
                  "status", "sentiment", "score", "analyzed_at", "created_at"]


def cmd_export(args):
    """export: CSV · 엑셀 · JSONL 내보내기 (Day 3).
    --rating-min은 storage.query_reviews가 지원하지 않아 Python 쪽에서 걸러낸다."""
    rows = storage.query_reviews(sentiment=args.sentiment)
    if args.rating_min is not None:
        rows = [r for r in rows if (_rating_int(r.get("rating")) or 0) >= args.rating_min]

    if not rows:
        logger.warning("export: 대상 0건 — 필터 조건을 확인하세요")
        print("[조건에 맞는 리뷰가 없습니다]")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fmt = args.format
    ext = {"csv": "csv", "excel": "xlsx", "jsonl": "jsonl"}[fmt]
    path = os.path.join(OUTPUT_DIR, f"export_{datetime.now():%Y%m%d_%H%M%S}.{ext}")

    records = [{c: r.get(c) for c in EXPORT_COLUMNS} for r in rows]
    if fmt == "csv":
        pd.DataFrame(records).to_csv(path, index=False, encoding="utf-8-sig")
    elif fmt == "excel":
        pd.DataFrame(records).to_excel(path, index=False)
    else:  # jsonl — 한 줄에 리뷰 1건
        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[INFO] {len(rows)}건 내보내기 완료 → {path}")
    logger.info("export: %s %d건 저장 (%s)", fmt, len(rows), path)
