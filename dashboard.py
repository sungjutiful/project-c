"""
dashboard.py - E 담당
차트 4종(감정분포/5일 단위 시간별추이/별점x감정/제품별 평균별점) PNG 저장
+ 종합 리포트 생성
"""

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 화면 없이도 PNG 파일 저장 가능

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import MaxNLocator

from storage import get_all_reviews, get_latest_extraction


# 프로젝트 기준 경로
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
OUTPUT_DIR = BASE_DIR / "output"


def load_config():
    """config.json 설정을 읽는다. 파일이 없거나 잘못되면 기본값을 사용한다."""

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as file:
            return json.load(file)

    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def setup_korean_font():
    """운영체제에서 사용 가능한 한글 폰트를 찾아 matplotlib에 적용한다."""

    preferred_fonts = [
        "AppleGothic",       # macOS
        "Malgun Gothic",     # Windows
        "NanumGothic",       # Linux
        "Noto Sans CJK KR",
    ]

    available_fonts = {
        font.name for font in font_manager.fontManager.ttflist
    }

    for font_name in preferred_fonts:
        if font_name in available_fonts:
            plt.rcParams["font.family"] = font_name
            break

    # 마이너스(-) 기호 깨짐 방지
    plt.rcParams["axes.unicode_minus"] = False


def create_sentiment_chart(reviews):
    """분석 완료된 리뷰의 긍정/중립/부정 분포를 막대그래프로 저장한다."""

    sentiment_order = [
        "positive",
        "neutral",
        "negative",
    ]

    sentiment_labels = {
        "positive": "긍정",
        "neutral": "중립",
        "negative": "부정",
    }

    sentiment_colors = {
        "positive": "#4C78A8",
        "neutral": "#A0A0A0",
        "negative": "#E45756",
    }

    counts = Counter(
        review.get("sentiment")
        for review in reviews
        if review.get("sentiment") in sentiment_order
    )

    total_analyzed = sum(counts.values())

    if total_analyzed == 0:
        print(
            "[dashboard] 감정 분석이 완료된 리뷰가 없어 "
            "감정 분포 차트를 생성하지 않았습니다."
        )
        return None

    labels = [
        sentiment_labels[item]
        for item in sentiment_order
    ]

    values = [
        counts[item]
        for item in sentiment_order
    ]

    colors = [
        sentiment_colors[item]
        for item in sentiment_order
    ]

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    config = load_config()
    chart_dpi = config.get("chart_dpi", 150)

    fig, ax = plt.subplots(
        figsize=(8, 5)
    )

    bars = ax.bar(
        labels,
        values,
        color=colors,
    )

    ax.set_title(
        "고객 리뷰 감정 분포",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_xlabel("감정")
    ax.set_ylabel("리뷰 수")

    ax.yaxis.set_major_locator(
        MaxNLocator(integer=True)
    )

    for bar, count in zip(bars, values):
        percentage = (
            count / total_analyzed * 100
        )

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{count}건\n({percentage:.1f}%)",
            ha="center",
            va="bottom",
        )

    max_value = max(values)

    ax.set_ylim(
        0,
        max_value * 1.25 if max_value > 0 else 1,
    )

    fig.tight_layout()

    output_path = (
        OUTPUT_DIR
        / "sentiment_distribution.png"
    )

    fig.savefig(
        output_path,
        dpi=chart_dpi,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        f"[dashboard] 감정 분포 차트 저장 완료: "
        f"{output_path} "
        f"(분석 리뷰 {total_analyzed}건)"
    )

    return output_path


def create_time_trend_chart(reviews):
    """5일 단위로 긍정/중립/부정 리뷰 수의 변화를 선그래프로 저장한다."""

    sentiment_order = [
        "positive",
        "neutral",
        "negative",
    ]

    sentiment_labels = {
        "positive": "긍정",
        "neutral": "중립",
        "negative": "부정",
    }

    sentiment_colors = {
        "positive": "#4C78A8",
        "neutral": "#A0A0A0",
        "negative": "#E45756",
    }

    # 유효한 리뷰 날짜 + 감정만 추출
    valid_reviews = []

    for review in reviews:
        sentiment = review.get("sentiment")
        review_date = review.get("review_date")

        if sentiment not in sentiment_order or not review_date:
            continue

        try:
            parsed_date = datetime.fromisoformat(
                str(review_date).strip()
            ).date()

        except (ValueError, TypeError):
            continue

        valid_reviews.append(
            (parsed_date, sentiment)
        )

    if not valid_reviews:
        print(
            "[dashboard] 날짜와 감정 정보가 있는 리뷰가 없어 "
            "시간별 감정 추이 차트를 생성하지 않았습니다."
        )
        return None

    # 가장 이른 리뷰 날짜를 기준으로 5일 단위 집계
    start_date = min(
        review_date
        for review_date, _ in valid_reviews
    )

    period_counts = defaultdict(Counter)

    for review_date, sentiment in valid_reviews:
        days_from_start = (
            review_date - start_date
        ).days

        period_index = (
            days_from_start // 5
        )

        period_start = (
            start_date
            + timedelta(days=period_index * 5)
        )

        period_counts[
            period_start
        ][sentiment] += 1

    dates = sorted(
        period_counts.keys()
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    config = load_config()
    chart_dpi = config.get("chart_dpi", 150)

    fig, ax = plt.subplots(
        figsize=(11, 5)
    )

    for sentiment in sentiment_order:
        values = [
            period_counts[date][sentiment]
            for date in dates
        ]

        ax.plot(
            dates,
            values,
            marker="o",
            markersize=6,
            linewidth=2.5,
            label=sentiment_labels[sentiment],
            color=sentiment_colors[sentiment],
        )

    ax.set_title(
        "5일 단위 고객 리뷰 감정 추이",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_xlabel("기간 시작일")
    ax.set_ylabel("리뷰 수")

    ax.yaxis.set_major_locator(
        MaxNLocator(integer=True)
    )

    ax.legend(
        title="감정"
    )

    ax.grid(
        axis="y",
        alpha=0.25,
    )

    # 5일 단위 시작 날짜를 X축에 표시
    ax.set_xticks(dates)

    ax.set_xticklabels(
        [
            date.strftime("%m-%d")
            for date in dates
        ],
        rotation=45,
        ha="right",
    )

    fig.tight_layout()

    output_path = (
        OUTPUT_DIR
        / "sentiment_time_trend.png"
    )

    fig.savefig(
        output_path,
        dpi=chart_dpi,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        "[dashboard] 5일 단위 감정 추이 차트 저장 완료: "
        f"{output_path}"
    )

    return output_path


def create_rating_sentiment_chart(reviews):
    """별점별 긍정/중립/부정 리뷰 분포를 누적 막대그래프로 저장한다."""

    sentiment_order = [
        "positive",
        "neutral",
        "negative",
    ]

    sentiment_labels = {
        "positive": "긍정",
        "neutral": "중립",
        "negative": "부정",
    }

    sentiment_colors = {
        "positive": "#4C78A8",
        "neutral": "#A0A0A0",
        "negative": "#E45756",
    }

    ratings = [
        1,
        2,
        3,
        4,
        5,
    ]

    rating_counts = {
        rating: Counter()
        for rating in ratings
    }

    for review in reviews:
        sentiment = review.get("sentiment")
        rating = review.get("rating")

        if sentiment not in sentiment_order:
            continue

        try:
            rating = int(rating)

        except (TypeError, ValueError):
            continue

        if rating not in ratings:
            continue

        rating_counts[
            rating
        ][sentiment] += 1

    total_analyzed = sum(
        sum(
            rating_counts[rating].values()
        )
        for rating in ratings
    )

    if total_analyzed == 0:
        print(
            "[dashboard] 별점과 감정 정보가 있는 리뷰가 없어 "
            "별점별 감정 분포 차트를 생성하지 않았습니다."
        )
        return None

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    config = load_config()
    chart_dpi = config.get("chart_dpi", 150)

    fig, ax = plt.subplots(
        figsize=(9, 5)
    )

    bottom = [
        0
    ] * len(ratings)

    for sentiment in sentiment_order:
        values = [
            rating_counts[
                rating
            ][sentiment]
            for rating in ratings
        ]

        ax.bar(
            ratings,
            values,
            bottom=bottom,
            label=sentiment_labels[
                sentiment
            ],
            color=sentiment_colors[
                sentiment
            ],
            width=0.6,
        )

        bottom = [
            current + value
            for current, value
            in zip(bottom, values)
        ]

    ax.set_title(
        "별점별 고객 리뷰 감정 분포",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_xlabel("별점")
    ax.set_ylabel("리뷰 수")

    ax.set_xticks(ratings)

    ax.set_xticklabels(
        [
            f"{rating}점"
            for rating in ratings
        ]
    )

    ax.yaxis.set_major_locator(
        MaxNLocator(integer=True)
    )

    ax.legend(
        title="감정"
    )

    ax.grid(
        axis="y",
        alpha=0.25,
    )

    fig.tight_layout()

    output_path = (
        OUTPUT_DIR
        / "rating_sentiment_distribution.png"
    )

    fig.savefig(
        output_path,
        dpi=chart_dpi,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        "[dashboard] 별점별 감정 분포 차트 저장 완료: "
        f"{output_path}"
    )

    return output_path


def create_product_rating_chart(reviews):
    """제품별 평균 별점을 막대그래프로 저장한다."""

    product_ratings = defaultdict(list)

    for review in reviews:
        product = review.get("product")
        rating = review.get("rating")

        if not product:
            continue

        product_name = str(
            product
        ).strip()

        try:
            rating = int(rating)

        except (TypeError, ValueError):
            continue

        if rating < 1 or rating > 5:
            continue

        product_ratings[
            product_name
        ].append(
            rating
        )

    if not product_ratings:
        print(
            "[dashboard] 제품과 별점 정보가 있는 리뷰가 없어 "
            "제품별 평균 별점 차트를 생성하지 않았습니다."
        )
        return None

    product_stats = []

    for product, ratings in product_ratings.items():
        average_rating = (
            sum(ratings) / len(ratings)
        )

        product_stats.append(
            (
                product,
                average_rating,
                len(ratings),
            )
        )

    product_stats.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    products = [
        item[0]
        for item in product_stats
    ]

    averages = [
        item[1]
        for item in product_stats
    ]

    counts = [
        item[2]
        for item in product_stats
    ]

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    config = load_config()
    chart_dpi = config.get("chart_dpi", 150)

    fig, ax = plt.subplots(
        figsize=(9, 5)
    )

    bars = ax.bar(
        products,
        averages,
        width=0.6,
    )

    ax.set_title(
        "제품별 평균 별점 비교",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_xlabel("제품")
    ax.set_ylabel("평균 별점")

    ax.set_ylim(
        0,
        5,
    )

    for bar, average, count in zip(
        bars,
        averages,
        counts,
    ):
        ax.text(
            bar.get_x()
            + bar.get_width() / 2,
            bar.get_height() + 0.08,
            f"{average:.2f}점\n({count}건)",
            ha="center",
            va="bottom",
        )

    ax.grid(
        axis="y",
        alpha=0.25,
    )

    fig.tight_layout()

    output_path = (
        OUTPUT_DIR
        / "product_average_rating.png"
    )

    fig.savefig(
        output_path,
        dpi=chart_dpi,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        "[dashboard] 제품별 평균 별점 차트 저장 완료: "
        f"{output_path}"
    )

    return output_path


def generate_report(reviews):
    """리뷰 통계와 AI 추출 결과를 종합하여 Markdown 리포트를 생성한다."""

    if not reviews:
        print(
            "[dashboard] 리포트를 생성할 리뷰가 없습니다."
        )
        return None

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    sentiment_order = [
        "positive",
        "neutral",
        "negative",
    ]

    sentiment_labels = {
        "positive": "긍정",
        "neutral": "중립",
        "negative": "부정",
    }

    # ----------------------------
    # 1. 기본 통계
    # ----------------------------
    total_reviews = len(reviews)

    analyzed_reviews = [
        review
        for review in reviews
        if review.get(
            "sentiment"
        ) in sentiment_order
    ]

    analyzed_count = len(
        analyzed_reviews
    )

    analysis_rate = (
        analyzed_count
        / total_reviews
        * 100
        if total_reviews > 0
        else 0
    )

    # ----------------------------
    # 2. 평균 별점
    # ----------------------------
    valid_ratings = []

    for review in reviews:
        try:
            rating = int(
                review.get("rating")
            )

        except (TypeError, ValueError):
            continue

        if 1 <= rating <= 5:
            valid_ratings.append(
                rating
            )

    average_rating = (
        sum(valid_ratings)
        / len(valid_ratings)
        if valid_ratings
        else 0
    )

    # ----------------------------
    # 3. 평균 감정 신뢰도
    # ----------------------------
    valid_scores = []

    for review in analyzed_reviews:
        try:
            score = float(
                review.get("score")
            )

        except (TypeError, ValueError):
            continue

        if 0 <= score <= 1:
            valid_scores.append(
                score
            )

    average_confidence = (
        sum(valid_scores)
        / len(valid_scores)
        if valid_scores
        else 0
    )

    # ----------------------------
    # 4. 감정별 통계
    # ----------------------------
    sentiment_counts = Counter(
        review.get("sentiment")
        for review in analyzed_reviews
    )

    # ----------------------------
    # 5. TOP 3 제품
    # ----------------------------
    product_counts = Counter(
        str(
            review.get("product")
        ).strip()
        for review in reviews
        if review.get("product")
    )

    top_products = (
        product_counts.most_common(3)
    )

    # ----------------------------
    # 6. AI 추출 결과
    # ----------------------------
    extraction = (
        get_latest_extraction()
    )

    report_lines = [
        "# 고객 리뷰 종합 분석 리포트",
        "",
        "## 1. 기본 현황",
        "",
        f"- 전체 정제 리뷰: **{total_reviews}건**",
        f"- 감정 분석 완료 리뷰: **{analyzed_count}건**",
        f"- 감정 분석 완료율: **{analysis_rate:.1f}%**",
        f"- 평균 별점: **{average_rating:.2f} / 5.00**",
        f"- 평균 감정 신뢰도: **{average_confidence:.2f}**",
        "",
        "## 2. 감정 분포",
        "",
    ]

    for sentiment in sentiment_order:
        count = sentiment_counts[
            sentiment
        ]

        percentage = (
            count
            / analyzed_count
            * 100
            if analyzed_count > 0
            else 0
        )

        report_lines.append(
            f"- {sentiment_labels[sentiment]}: "
            f"**{count}건 ({percentage:.1f}%)**"
        )

    report_lines.extend(
        [
            "",
            "## 3. 리뷰 수 기준 TOP 3 제품",
            "",
        ]
    )

    if top_products:
        for rank, (
            product,
            count,
        ) in enumerate(
            top_products,
            start=1,
        ):
            report_lines.append(
                f"{rank}. {product} - **{count}건**"
            )

    else:
        report_lines.append(
            "- 제품 정보가 없습니다."
        )

    report_lines.extend(
        [
            "",
            "## 4. AI 분석 인사이트",
            "",
        ]
    )

    # extraction이 있을 때만 관련 변수 사용
    if extraction:
        target = (
            extraction.get("target")
            or "전체 리뷰"
        )

        positive_keywords = (
            extraction.get("pos_keywords")
            or extraction.get("positive_keywords")
        )

        negative_keywords = (
            extraction.get("neg_keywords")
            or extraction.get("negative_keywords")
        )

        general_keywords = (
            extraction.get("keywords")
        )

        summary = (
            extraction.get("summary")
            or "-"
        )

        suggestions = (
            extraction.get("suggestions")
            or "-"
        )

        report_lines.append(
            f"- 분석 대상: **{target}**"
        )

        if (
            positive_keywords
            and negative_keywords
        ):
            report_lines.append(
                "- 주요 긍정 키워드: "
                f"{positive_keywords}"
            )

            report_lines.append(
                "- 주요 부정 키워드: "
                f"{negative_keywords}"
            )

        elif general_keywords:
            report_lines.append(
                "- 주요 키워드: "
                f"{general_keywords}"
            )

        elif positive_keywords:
            report_lines.append(
                "- 주요 키워드: "
                f"{positive_keywords}"
            )

        elif negative_keywords:
            report_lines.append(
                "- 주요 키워드: "
                f"{negative_keywords}"
            )

        else:
            report_lines.append(
                "- 저장된 AI 키워드가 없습니다."
            )

        if summary != "-":
            report_lines.append(
                f"- AI 요약: {summary}"
            )

        if suggestions != "-":
            report_lines.append(
                f"- 개선 제안: {suggestions}"
            )

    else:
        report_lines.append(
            "- 저장된 AI 키워드/요약 추출 결과가 없습니다."
        )

    # ----------------------------
    # 7. 생성된 차트 목록
    # ----------------------------
    report_lines.extend(
        [
            "",
            "## 5. 생성 차트",
            "",
            "- 감정 분포: `sentiment_distribution.png`",
            "- 5일 단위 감정 추이: `sentiment_time_trend.png`",
            "- 별점별 감정 분포: `rating_sentiment_distribution.png`",
            "- 제품별 평균 별점 비교: `product_average_rating.png`",
            "",
        ]
    )

    report_text = "\n".join(
        report_lines
    )

    output_path = (
        OUTPUT_DIR
        / "review_report.md"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            report_text
        )

    # 콘솔에도 리포트 출력
    print()
    print("=" * 60)
    print("고객 리뷰 종합 분석 리포트")
    print("=" * 60)

    print(
        f"전체 정제 리뷰: "
        f"{total_reviews}건"
    )

    print(
        f"감정 분석 완료: "
        f"{analyzed_count}건 "
        f"({analysis_rate:.1f}%)"
    )

    print(
        f"평균 별점: "
        f"{average_rating:.2f} / 5.00"
    )

    print(
        f"평균 감정 신뢰도: "
        f"{average_confidence:.2f}"
    )

    print("-" * 60)

    for sentiment in sentiment_order:
        count = sentiment_counts[
            sentiment
        ]

        percentage = (
            count
            / analyzed_count
            * 100
            if analyzed_count > 0
            else 0
        )

        print(
            f"{sentiment_labels[sentiment]}: "
            f"{count}건 "
            f"({percentage:.1f}%)"
        )

    print("-" * 60)

    print(
        f"리포트 저장 완료: "
        f"{output_path}"
    )

    print("=" * 60)

    return output_path


def run_dashboard():
    """대시보드 생성을 실행한다."""

    setup_korean_font()

    reviews = get_all_reviews(
        status="clean"
    )

    if not reviews:
        print(
            "[dashboard] 정제된 리뷰가 없습니다."
        )
        return

    print(
        f"[dashboard] 정제 리뷰 "
        f"{len(reviews)}건을 불러왔습니다."
    )

    create_sentiment_chart(
        reviews
    )

    create_time_trend_chart(
        reviews
    )

    create_rating_sentiment_chart(
        reviews
    )

    create_product_rating_chart(
        reviews
    )

    generate_report(
        reviews
    )


if __name__ == "__main__":
    run_dashboard()