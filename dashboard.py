"""
dashboard.py - E 담당
차트 3종(감정분포/시간별추이/별점x감정) PNG 저장 + 종합 리포트 생성
"""

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 화면 없이도 PNG 파일을 저장할 수 있게 설정
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import MaxNLocator

from storage import get_all_reviews


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
        "NanumGothic",       # Linux / 설치 환경
        "Noto Sans CJK KR",
    ]

    available_fonts = {
        font.name for font in font_manager.fontManager.ttflist
    }

    for font_name in preferred_fonts:
        if font_name in available_fonts:
            plt.rcParams["font.family"] = font_name
            break

    # 마이너스(-) 기호가 깨지는 문제 방지
    plt.rcParams["axes.unicode_minus"] = False


def create_sentiment_chart(reviews):
    """분석 완료된 리뷰의 긍정/중립/부정 분포를 막대그래프로 저장한다."""

    sentiment_order = ["positive", "neutral", "negative"]

    sentiment_labels = {
        "positive": "긍정",
        "neutral": "중립",
        "negative": "부정",
    }

    # 긍정: 파랑 / 중립: 회색 / 부정: 빨강
    sentiment_colors = {
        "positive": "#4C78A8",
        "neutral": "#A0A0A0",
        "negative": "#E45756",
    }

    # 감정 분석이 완료된 리뷰만 집계
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

    # 출력 폴더가 없으면 자동 생성
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    config = load_config()
    chart_dpi = config.get("chart_dpi", 150)

    fig, ax = plt.subplots(figsize=(8, 5))

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

    # 리뷰 수는 0, 1, 2, 3 ... 정수 단위로 표시
    ax.yaxis.set_major_locator(
        MaxNLocator(integer=True)
    )

    # 막대 위에 건수와 비율 표시
    for bar, count in zip(bars, values):
        percentage = count / total_analyzed * 100

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{count}건\n({percentage:.1f}%)",
            ha="center",
            va="bottom",
        )

    # 가장 높은 막대 위의 글자가 잘리지 않도록 여백 확보
    max_value = max(values)
    ax.set_ylim(
        0,
        max_value * 1.25 if max_value > 0 else 1,
    )

    fig.tight_layout()

    output_path = OUTPUT_DIR / "sentiment_distribution.png"

    fig.savefig(
        output_path,
        dpi=chart_dpi,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        f"[dashboard] 감정 분포 차트 저장 완료: {output_path}"
        f" (분석 리뷰 {total_analyzed}건)"
    )

    return output_path

def create_time_trend_chart(reviews):
    """날짜별 긍정/중립/부정 리뷰 수의 변화를 선그래프로 저장한다."""

    sentiment_order = ["positive", "neutral", "negative"]

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

    # 날짜별 감정 리뷰 수 저장
    daily_counts = defaultdict(Counter)

    for review in reviews:
        sentiment = review.get("sentiment")
        review_date = review.get("review_date")

        # 분석되지 않은 리뷰나 날짜가 없는 리뷰는 제외
        if sentiment not in sentiment_order or not review_date:
            continue

        try:
            # YYYY-MM-DD 또는 ISO 형식 날짜 처리
            parsed_date = datetime.fromisoformat(
                str(review_date).strip()
            ).date()

        except (ValueError, TypeError):
            # 날짜 형식이 잘못된 리뷰는 차트에서 제외
            continue

        daily_counts[parsed_date][sentiment] += 1

    if not daily_counts:
        print(
            "[dashboard] 날짜와 감정 정보가 있는 리뷰가 없어 "
            "시간별 감정 추이 차트를 생성하지 않았습니다."
        )
        return None

    dates = sorted(daily_counts.keys())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    config = load_config()
    chart_dpi = config.get("chart_dpi", 150)

    fig, ax = plt.subplots(figsize=(10, 5))

    for sentiment in sentiment_order:
        values = [
            daily_counts[date][sentiment]
            for date in dates
        ]

        ax.plot(
            dates,
            values,
            marker="o",
            markersize=7,
            linewidth=3,
            label=sentiment_labels[sentiment],
            color=sentiment_colors[sentiment],
    )

    ax.set_title(
        "시간별 고객 리뷰 감정 추이",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_xlabel("리뷰 날짜")
    ax.set_ylabel("리뷰 수")

    # 리뷰 수는 정수 단위로 표시
    ax.yaxis.set_major_locator(
        MaxNLocator(integer=True)
    )

    ax.legend(title="감정")
    ax.grid(axis="y", alpha=0.25)

   # 실제 리뷰 날짜만 X축에 표시
    ax.set_xticks(dates)
    ax.set_xticklabels(
        [date.strftime("%m-%d") for date in dates],
        rotation=0,
    )

    fig.tight_layout()

    output_path = OUTPUT_DIR / "sentiment_time_trend.png"

    fig.savefig(
        output_path,
        dpi=chart_dpi,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        f"[dashboard] 시간별 감정 추이 차트 저장 완료: "
        f"{output_path}"
    )

    return output_path
def create_rating_sentiment_chart(reviews):
        """별점별 긍정/중립/부정 리뷰 분포를 누적 막대그래프로 저장한다."""

        sentiment_order = ["positive", "neutral", "negative"]

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

        ratings = [1, 2, 3, 4, 5]

        # 별점별 감정 리뷰 수 집계
        rating_counts = {
            rating: Counter()
            for rating in ratings
        }

        for review in reviews:
            sentiment = review.get("sentiment")
            rating = review.get("rating")

            # 감정 분석이 완료되지 않은 리뷰는 제외
            if sentiment not in sentiment_order:
                continue

            try:
                rating = int(rating)
            except (TypeError, ValueError):
                continue

            # 별점 범위가 1~5인 데이터만 사용
            if rating not in ratings:
                continue

            rating_counts[rating][sentiment] += 1

        total_analyzed = sum(
            sum(rating_counts[rating].values())
            for rating in ratings
        )

        if total_analyzed == 0:
            print(
                "[dashboard] 별점과 감정 정보가 있는 리뷰가 없어 "
                "별점별 감정 분포 차트를 생성하지 않았습니다."
            )
            return None

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        config = load_config()
        chart_dpi = config.get("chart_dpi", 150)

        fig, ax = plt.subplots(figsize=(9, 5))

        bottom = [0] * len(ratings)

        for sentiment in sentiment_order:
            values = [
                rating_counts[rating][sentiment]
                for rating in ratings
            ]

            ax.bar(
                ratings,
                values,
                bottom=bottom,
                label=sentiment_labels[sentiment],
                color=sentiment_colors[sentiment],
                width=0.6,
            )

            bottom = [
                current + value
                for current, value in zip(bottom, values)
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
            [f"{rating}점" for rating in ratings]
        )

        # 리뷰 수는 정수 단위로 표시
        ax.yaxis.set_major_locator(
            MaxNLocator(integer=True)
        )

        ax.legend(title="감정")
        ax.grid(axis="y", alpha=0.25)

        fig.tight_layout()

        output_path = OUTPUT_DIR / "rating_sentiment_distribution.png"

        fig.savefig(
            output_path,
            dpi=chart_dpi,
            bbox_inches="tight",
        )

        plt.close(fig)

        print(
            f"[dashboard] 별점별 감정 분포 차트 저장 완료: "
            f"{output_path}"
        )

        return output_path

def run_dashboard():
    """대시보드 생성을 실행한다."""
    setup_korean_font()

    reviews = get_all_reviews(status="clean")

    if not reviews:
        print("[dashboard] 정제된 리뷰가 없습니다.")
        return

    print(
        f"[dashboard] 정제 리뷰 {len(reviews)}건을 불러왔습니다."
    )

    create_sentiment_chart(reviews)
    create_time_trend_chart(reviews)
    create_rating_sentiment_chart(reviews)
if __name__ == "__main__":
    run_dashboard()
   
