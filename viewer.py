"""
viewer.py — D 담당
list:  저장된 리뷰 전체를 번호와 함께 출력 (Day 1 초안)
show / stats / export: Day 2~3에 채운다
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
    """list 초안: 저장된 리뷰 전체를 번호와 함께 출력 (Day 1).
    Day 2에 필터·페이지네이션·정렬로 고도화한다."""
    rows = storage.get_all_reviews()
    print(f"=== 리뷰 목록 (총 {len(rows)}건) ===")
    if not rows:
        logger.warning("list 조회 결과 0건 — import 미실행 가능성")
        print("[저장된 리뷰가 없습니다 — import를 실행한 뒤 다시 확인하세요]")
        return
    for r in rows:
        date = r.get("review_date") or "-"
        print(
            f"[{r['id']}] {_stars(r.get('rating'))} | {date} | "
            f"{_truncate(r.get('text'))} | {_sentiment(r)}"
        )
    logger.info("list 조회 %d건 출력", len(rows))
