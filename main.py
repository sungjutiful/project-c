"""
main.py
9개 서브커맨드(import, clean, analyze, extract, list, show, stats, dashboard, export)의
"접수처"만 만든다. 실제 로직은 각 담당자의 모듈(importer.py, analyzer.py, viewer.py,
dashboard.py)에서 채운다. 지금은 뼈대만 있어도 --help로 9개가 보이면 성공.
"""

import argparse
import logging
import storage

# ── 공통 로거 설정 (전원 사용) ──────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("app.log", encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger("review_dashboard")


def build_parser():
    parser = argparse.ArgumentParser(description="AI 고객 리뷰 감정 분석 대시보드")
    sub = parser.add_subparsers(dest="command")

    p_import = sub.add_parser("import", help="[B] 리뷰 파일을 raw로 저장")
    p_import.add_argument("--file", required=True)

    sub.add_parser("clean", help="[B] raw 리뷰를 정제")

    p_analyze = sub.add_parser("analyze", help="[C] AI 감정 분석")
    p_analyze.add_argument("--all", action="store_true", dest="all_")
    p_analyze.add_argument("--id", type=int, dest="review_id")
    p_analyze.add_argument("--unanalyzed", action="store_true")
    p_analyze.add_argument("--limit", type=int)

    p_extract = sub.add_parser("extract", help="[C] 키워드·요약·개선제안 추출")
    p_extract.add_argument("--sentiment")
    p_extract.add_argument("--product")

    p_list = sub.add_parser("list", help="[D] 리뷰 목록 조회")
    p_list.add_argument("--sentiment")
    p_list.add_argument("--rating", type=int)
    p_list.add_argument("--date-from")
    p_list.add_argument("--date-to")
    p_list.add_argument("--page", type=int, default=1)
    p_list.add_argument("--size", type=int, default=5)
    p_list.add_argument("--sort", choices=["date", "rating"], default="date")

    p_show = sub.add_parser("show", help="[D] 리뷰 상세 조회")
    p_show.add_argument("--id", type=int, required=True)

    sub.add_parser("stats", help="[D] 통계 요약")
    sub.add_parser("dashboard", help="[E] 차트 3종 + 종합 리포트")

    p_export = sub.add_parser("export", help="[D] 결과 내보내기")
    p_export.add_argument("--format", choices=["csv", "excel", "jsonl"], default="csv")
    p_export.add_argument("--sentiment")
    p_export.add_argument("--rating-min", type=int, dest="rating_min")

    return parser


def main():

    storage.init_db()

    parser = build_parser()

    args = parser.parse_args()

    if args.command == "import":

        import importer

        importer.import_reviews(args.file)

    elif args.command == "clean":

        import importer

        importer.clean_reviews()
    elif args.command == "analyze":
        import analyzer
        if args.review_id:
            reviews = [storage.get_review_by_id(args.review_id)]
            reviews = [r for r in reviews if r]
            unanalyzed_only = False
        elif args.all_:
            reviews = storage.get_all_reviews(status="clean")
            unanalyzed_only = False
        else:
            reviews = storage.get_unanalyzed(limit=args.limit)
            unanalyzed_only = False

        total = len(reviews)
        print(f"[INFO] 분석 대상: {total}건")
        results = analyzer.analyze_reviews(reviews, unanalyzed_only=unanalyzed_only, limit=args.limit)
        for i, r in enumerate(results, start=1):
            storage.update_sentiment(r["id"], r["sentiment"], r["score"])
            print(f"[INFO] [{i}/{len(results)}] ID={r['id']} 분석 완료: {r['sentiment']} ({r['score']})")
        print(f"[INFO] 분석 완료: {len(results)}건 성공, {total - len(results)}건 실패/스킵")

    elif args.command == "extract":
        import analyzer
        reviews = storage.query_reviews(sentiment=args.sentiment)
        if args.product:
            reviews = [r for r in reviews if r.get("product") == args.product]
        reviews = reviews[:30]

        condition_desc = f"sentiment={args.sentiment or '전체'}, product={args.product or '전체'}"
        print(f"[INFO] 추출 대상: {condition_desc} {len(reviews)}건")
        result = analyzer.extract_insights(reviews, target_condition=condition_desc)

        if result:
            keywords = ", ".join(result.get("keywords", []))
            summary = result.get("summary", "")
            suggestions = result.get("suggestions", "")
            storage.insert_extraction(condition_desc, keywords, "", summary, suggestions)
            print("[INFO] 추출 완료\n")
            print(f"[주요 키워드]\n{keywords}")
            print(f"\n[요약]\n{summary}")
            print(f"\n[개선 제안]\n{suggestions}")
        else:
            print("[WARNING] 추출 실패 (API 에러 또는 대상 리뷰 없음)")

    elif args.command == "list":

        print("[준비 중] list")

    elif args.command == "show":

        print(f"[준비 중] show {args.id}")

    elif args.command == "stats":

        print("[준비 중] stats")

    elif args.command == "dashboard":

        print("[준비 중] dashboard")

    elif args.command == "export":

        print("[준비 중] export")

    else:

        parser.print_help()


if __name__ == "__main__":

    main()
 
