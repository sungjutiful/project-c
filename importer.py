"""
importer.py — B 담당
import: CSV/엑셀에서 리뷰를 읽어 raw로 저장 (storage.insert_review 사용)
clean: 정제 규칙 5가지 적용 + 중복 skip/upsert (storage.mark_cleaned 사용)
"""
"""

importer.py — B 담당

import: CSV/엑셀에서 리뷰를 읽어 raw로 저장 (storage.insert_review 사용)

clean: 정제 규칙 5가지 적용 + 중복 skip/upsert (storage.mark_cleaned 사용)

"""

import json

import logging

import pandas as pd

import storage

logger = logging.getLogger("review_dashboard")


def _load_config():

    with open("config.json", encoding="utf-8") as f:

        return json.load(f)


def import_reviews(file_path):

    config = _load_config()

    policy = config.get("duplicate_policy", "skip")

    df = pd.read_csv(file_path, encoding="utf-8-sig")

    if "review_date" not in df.columns and "created_at" in df.columns:

        df = df.rename(columns={"created_at": "review_date"})

    saved = 0

    skipped = 0

    for _, row in df.iterrows():

        text = str(row.get("text", "")).strip()

        if not text or text.lower() == "nan":

            logger.warning(f"내용 없는 리뷰 건너뜀: {row.to_dict()}")

            continue

        if storage.text_exists(text):

            if policy == "skip":

                skipped += 1

                continue

            else:

                logger.warning(f"upsert 정책이지만 아직 지원되지 않아 건너뜀: {text[:20]}...")

                skipped += 1

                continue

        product = row.get("product")

        rating = row.get("rating")

        review_date = row.get("review_date")

        storage.insert_review(product, rating, review_date, text)

        saved += 1

    print(f"{saved}건 저장, {skipped}건 중복(정책: {policy})으로 건너뜀")


def clean_reviews():

    config = _load_config()

    min_len = config.get("min_review_length", 5)

    raw_reviews = storage.get_all_reviews(status="raw")

    cleaned = 0

    for r in raw_reviews:

        text = str(r["text"]).strip()

        if len(text) < min_len:

            logger.warning(f"짧은 리뷰 건너뜀 (id={r['id']}, {len(text)}자): {text}")

            continue

        rating = r["rating"]

        try:

            rating = int(rating)

            if not (1 <= rating <= 5):

                logger.warning(f"별점 범위 벗어남 (id={r['id']}): {rating}")

                rating = None

        except (TypeError, ValueError):

            rating = None

        review_date = r["review_date"]

        parsed_date = pd.to_datetime(review_date, errors="coerce")

        review_date = parsed_date.strftime("%Y-%m-%d") if pd.notna(parsed_date) else None

        storage.mark_cleaned(r["id"], text, rating, review_date)

        cleaned += 1

    print(f"{cleaned}건 정제 완료 (원본 {len(raw_reviews)}건 중)")
 
