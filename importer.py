"""
importer.py — B 담당 (데이터 수집·정제)

import : CSV/엑셀 파일을 읽어 reviews 테이블에 status='raw'로 저장한다.
         같은 text가 이미 있으면 config.json의 duplicate_policy에 따라
         skip(건너뜀) 또는 upsert(기존 행을 덮어씀) 처리한다.
clean  : status='raw'인 리뷰에 정제 규칙 5가지를 순서대로 적용한다.
         통과 → text_clean을 채우고 status='clean'
         탈락 → WARNING 로그를 남기고 raw 상태로 둔다 (원본은 지우지 않는다)

DB는 절대 직접 열지 않고 storage.py 함수만 사용한다. (팀 규칙)
  storage.text_exists(text)                                  -> True / False
  storage.insert_review(product, rating, review_date, text)
  storage.update_review_by_text(text, product, rating, review_date)   <- upsert용, A에게 요청
  storage.get_all_reviews(status="raw")                      -> 리뷰 목록
  storage.mark_cleaned(review_id, text_clean, rating, review_date)

실행 예시
  python main.py import --file data/sample_reviews.csv
  python main.py clean
"""

import json
import logging
import os
import warnings

import pandas as pd

import storage

logger = logging.getLogger("review_dashboard")

# config.json에 값이 없을 때 쓰는 기본값
DEFAULT_POLICY = "skip"     # 중복 정책: skip 또는 upsert
DEFAULT_MIN_LENGTH = 10     # 이 글자 수 미만이면 "짧은 리뷰"로 제외


# ──────────────────────────────────────────────────────────────
# 공통 도우미 함수 (import와 clean이 같이 씀)
# ──────────────────────────────────────────────────────────────

def _load_config():
    """config.json을 읽어 dict로 돌려준다. 문제가 있으면 기본값으로 계속 진행한다."""
    try:
        with open("config.json", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("config.json이 없어 기본값(skip, 10자)으로 진행합니다")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"config.json 형식 오류 (주석 // 이 들어있지 않은지 확인): {e}")
        return {}


def _cell(row, column):
    """CSV/엑셀의 한 칸을 문자열로 꺼낸다. 빈 칸·NaN은 ''로 통일한다."""
    value = row.get(column, "")
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):   # 빈 칸이 NaN으로 들어오는 경우
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _normalize_text(value):
    """규칙 2. 텍스트 정규화: 앞뒤 공백 제거 + 연속 공백·줄바꿈을 한 칸으로."""
    if value is None:
        return ""
    text = str(value)
    if text.strip().lower() == "nan":
        return ""
    return " ".join(text.split())


def _parse_rating(value):
    """'5', '5.0', 5 → 5.  빈 값·글자('five')·소수(4.5)는 None."""
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if not number.is_integer():
        return None
    return int(number)


def _normalize_date(value):
    """규칙 4. 날짜 통일: '2026/07/18', '2026-07-18 00:00:00' 등 → '2026-07-18'.
    빈 값이거나 해석할 수 없으면 None을 돌려준다 (판단은 부른 쪽에서)."""
    if value is None or str(value).strip() == "":
        return None
    with warnings.catch_warnings():            # pandas의 '형식 추정' 경고 문구 숨김
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(str(value).strip(), errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.strftime("%Y-%m-%d")


def _read_file(file_path):
    """CSV 또는 엑셀을 읽어 DataFrame으로. 모든 칸을 문자열로 읽고 빈 칸은 ''로 둔다."""
    if not os.path.exists(file_path):
        logger.error(f"파일을 찾을 수 없습니다: {file_path}")
        return None
    try:
        if file_path.lower().endswith((".xlsx", ".xls")):
            return pd.read_excel(file_path, dtype=str, keep_default_na=False)
        try:
            return pd.read_csv(file_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
        except UnicodeDecodeError:          # 엑셀에서 '다른 이름으로 저장'한 한글 CSV
            logger.warning("utf-8로 읽지 못해 cp949(엑셀 한글) 인코딩으로 다시 읽습니다")
            return pd.read_csv(file_path, encoding="cp949", dtype=str, keep_default_na=False)
    except Exception as e:
        logger.error(f"파일을 읽는 중 오류: {e}")
        return None


# ──────────────────────────────────────────────────────────────
# import  — python main.py import --file data/sample_reviews.csv
# ──────────────────────────────────────────────────────────────

def import_reviews(file_path):
    config = _load_config()
    policy = str(config.get("duplicate_policy", DEFAULT_POLICY)).lower()
    if policy not in ("skip", "upsert"):
        logger.warning(f"duplicate_policy 값이 이상해서 skip으로 처리합니다: {policy!r}")
        policy = "skip"
    if policy == "upsert" and not hasattr(storage, "update_review_by_text"):
        logger.error("upsert 정책은 storage.update_review_by_text 함수가 필요합니다 (A에게 요청). "
                     "이번 실행은 skip으로 처리합니다.")
        policy = "skip"

    df = _read_file(file_path)
    if df is None:
        return

    # 열 이름 약속: product, rating, review_date, text
    if "review_date" not in df.columns and "created_at" in df.columns:
        df = df.rename(columns={"created_at": "review_date"})
    if "text" not in df.columns:
        logger.error(f"'text' 열이 없어 import를 중단합니다. 현재 열: {list(df.columns)}")
        return

    saved = updated = skipped = empty = failed = 0

    for i, row in df.iterrows():
        line_no = i + 2                         # 1행은 제목줄이므로 실제 파일의 행 번호
        try:
            text = _cell(row, "text")
            if not text:                        # 내용이 없으면 저장할 수 없다 (text는 필수 필드)
                logger.warning(f"{line_no}행: 내용(text)이 비어 있어 저장하지 않음")
                empty += 1
                continue

            product = _cell(row, "product") or None
            rating_cell = _cell(row, "rating")
            rating = _parse_rating(rating_cell)
            if rating_cell and rating is None:  # '★★★★', 'five' 같은 값
                logger.warning(f"{line_no}행: 별점 {rating_cell!r}을 숫자로 읽을 수 없어 비워둠 (clean에서 제외됨)")
            review_date = _cell(row, "review_date") or None

            if storage.text_exists(text):       # 중복 판정 기준: text가 완전히 같음
                if policy == "upsert":
                    storage.update_review_by_text(text, product, rating, review_date)
                    updated += 1
                else:
                    skipped += 1
                continue

            storage.insert_review(product, rating, review_date, text)
            saved += 1

        except Exception as e:                  # 한 행이 이상해도 프로그램은 죽지 않는다
            failed += 1
            logger.error(f"{line_no}행 저장 실패, 건너뜀: {e}")

    dup_label = f"덮어쓰기 {updated}건" if policy == "upsert" else f"건너뜀 {skipped}건"
    logger.info(f"import 완료: {file_path} (정책: {policy})")
    print(f"저장 {saved}건 · 중복 {dup_label} · 내용 없음 {empty}건 · 실패 {failed}건  (파일 {len(df)}행)")


# ──────────────────────────────────────────────────────────────
# clean  — python main.py clean
# ──────────────────────────────────────────────────────────────

def clean_reviews():
    config = _load_config()
    min_len = int(config.get("short_review_min_length", DEFAULT_MIN_LENGTH))

    raw_reviews = storage.get_all_reviews(status="raw")
    total = len(raw_reviews)
    if total == 0:
        print("정제할 raw 리뷰가 없습니다. 먼저 import를 실행하세요.")
        return

    cleaned = rejected = 0

    for r in raw_reviews:
        review_id = r["id"]
        try:
            # 규칙 1. 필수 필드 검증 — text가 비어 있으면 제외
            #        (규칙 2의 정규화를 먼저 적용해서 공백만 있는 경우도 잡는다)
            text = _normalize_text(r["text"])
            if not text:
                logger.warning(f"[제외] id={review_id}: 내용(text)이 비어 있음")
                rejected += 1
                continue

            # 규칙 2. 텍스트 정규화 → text_clean (위 _normalize_text 결과)

            # 규칙 3. 별점 1~5 검증 — 범위 밖·숫자 아님·비어 있음은 제외
            rating = _parse_rating(r["rating"])
            if rating is None or not 1 <= rating <= 5:
                logger.warning(f"[제외] id={review_id}: 별점이 1~5가 아님 ({r['rating']!r})")
                rejected += 1
                continue

            # 규칙 4. 날짜 YYYY-MM-DD 통일 — 날짜는 선택 필드라 비어 있으면 허용,
            #        값이 있는데 해석할 수 없으면('어제', 2026-13-45) 제외
            raw_date = r["review_date"]
            review_date = _normalize_date(raw_date)
            if review_date is None and str(raw_date or "").strip() != "":
                logger.warning(f"[제외] id={review_id}: 날짜를 해석할 수 없음 ({raw_date!r})")
                rejected += 1
                continue

            # 규칙 5. 짧은 리뷰 제거 — config의 short_review_min_length 미만이면 제외
            if len(text) < min_len:
                logger.warning(f"[제외] id={review_id}: {min_len}자 미만 짧은 리뷰 ({len(text)}자): {text}")
                rejected += 1
                continue

            storage.mark_cleaned(review_id, text, rating, review_date)
            cleaned += 1

        except Exception as e:                  # 한 건이 이상해도 프로그램은 죽지 않는다
            rejected += 1
            logger.error(f"id={review_id} 정제 중 오류, 건너뜀: {e}")

    logger.info(f"clean 완료 (기준: {min_len}자 이상)")
    print(f"정제 {cleaned}건 · 제외 {rejected}건  (raw {total}건 중)")
