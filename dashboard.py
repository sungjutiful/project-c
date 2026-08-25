"""
dashboard.py — E 담당
차트 3종(감정분포/시간별추이/별점x감정) PNG 저장 + 종합 리포트 생성
"""
from storage import get_all_reviews

def test_data():
    reviews = get_all_reviews(status="clean")
    print(f"clean 리뷰 수: {len(reviews)}")

if __name__ == "__main__":
    test_data()
   
