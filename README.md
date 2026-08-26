# Project C — AI 고객 리뷰 감정 분석 대시보드

리뷰 CSV를 넣으면 AI가 감정을 분류하고, 키워드를 뽑고, 차트와 리포트를 만들어주는 CLI 프로그램입니다.

## 설치
```
pip install -r requirements.txt
```

## 설정
1. `config.example.json`을 복사해서 `config.json`으로 만들고, 발급받은 API 키를 넣으세요.
2. `config.json`은 절대 GitHub에 올리지 마세요 (.gitignore에 이미 포함됨).

## 실행 순서
```
python main.py import --file data/sample_reviews.csv
python main.py clean
python main.py analyze --unanalyzed
python main.py extract --sentiment negative
python main.py stats
python main.py list --sentiment negative
python main.py show 1
python main.py dashboard
python main.py export --format csv
```






## E. 대시보드 시각화 및 종합 리포트

`dashboard.py`는 정제 및 감정 분석이 완료된 리뷰 데이터를 조회하여
시각화 차트와 종합 분석 리포트를 생성합니다.

### 주요 기능

- 감정 분포 차트
  - 긍정 / 중립 / 부정 리뷰 건수와 비율을 막대그래프로 표시
  - 긍정은 파란색, 중립은 회색, 부정은 빨간색으로 구분

- 시간별 감정 추이 차트
  - 리뷰 작성일을 기준으로 긍정 / 중립 / 부정 리뷰 수의 변화를 선그래프로 표시
  - 실제 리뷰 날짜만 X축에 표시

- 별점별 감정 분포 차트
  - 별점 1~5점별 긍정 / 중립 / 부정 리뷰 분포를 누적 막대그래프로 표시
  - 별점과 AI 감정 분석 결과의 관계를 확인 가능

- 제품별 평균 별점 비교 차트
  - 제품별 평균 별점을 계산하여 막대그래프로 비교
  - 막대 위에 평균 별점과 리뷰 수를 함께 표시

- 종합 분석 리포트
  - 전체 정제 리뷰 수
  - 감정 분석 완료율
  - 평균 별점
  - 평균 감정 신뢰도
  - 감정별 리뷰 건수 및 비율
  - 리뷰 수 기준 TOP 3 제품
  - AI 키워드 / 전체 요약 / 개선 제안
  - 생성된 차트 목록
  - 콘솔 출력 및 Markdown 파일 저장

### 생성 파일

대시보드 실행 시 `output/` 폴더에 다음 결과물이 생성됩니다.

```text
output/
├── sentiment_distribution.png
├── sentiment_time_trend.png
├── rating_sentiment_distribution.png
├── product_average_rating.png
└── review_report.md
```
### 실행 방법

프로젝트 루트 디렉터리에서 다음 명령으로 실행합니다.

```bash
python3 main.py dashboard
```