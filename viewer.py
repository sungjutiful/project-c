"""
viewer.py — D 담당
list:  필터(감정·별점·기간) + 정렬 + 페이지네이션 (Day 2)
show:  리뷰 1건 상세 — 원문 + 분석 결과 (Day 2)
stats / export: Day 3에 채운다
"""

import logging

import storage

logger = logging.getLogger("review_dashboard")


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
