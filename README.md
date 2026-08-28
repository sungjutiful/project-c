# Project C — AI 고객 리뷰 감정 분석 대시보드

리뷰 CSV/엑셀을 넣으면 AI가 감정(긍정·부정·중립)을 분류하고, 키워드·요약·개선 제안을 뽑고,
차트와 종합 리포트를 만들어주는 CLI 기반 Python 프로그램입니다.

## 1. 미션 요약

고객 리뷰는 제품·서비스 품질을 가장 직접적으로 보여주는 지표지만, 사람이 수백~수천 건을 읽고 분석하기는 현실적으로 어렵습니다. 이 프로젝트는 리뷰 데이터를 수집·정제하고, AI로 감정 분석과 인사이트를 추출한 뒤, 시간에 따른 감정 변화·별점과 감정의 상관관계 등을 시각화·리포트로 만들어 비즈니스 의사결정에 활용할 수 있게 합니다.

## 2. 팀 구성 및 역할 분담

5인 1역할로 파일 단위 담당을 나누고, 통합(A)이 전체를 연결하는 방식으로 진행했습니다.

| 역할 | 담당 파일 | 담당 기능 |
|---|---|---|
| A(최성주) — 팀장·통합 | `main.py`, `storage.py` | 프로젝트 뼈대, DB 스키마 설계, 9개 서브커맨드 접수처, 각 팀원 모듈을 실제로 연결·검증, 공통 로거/설정 |
| B(신미영) — 데이터 수집·정제 | `importer.py` | `import`(CSV/엑셀 읽어 원본 저장, 중복 skip/upsert), `clean`(정제 규칙 5종 적용) |
| C(최주원) — AI 감정 분석·추출 | `analyzer.py` | `analyze`(OpenAI API로 감정·신뢰도 분석), `extract`(리뷰 묶음에서 키워드·요약·개선 제안 추출) |
| D(이종명) — 데이터 조회 | `viewer.py` | `list`(필터·정렬·페이지네이션), `show`(리뷰 상세), `stats`(통계 요약), `export`(CSV·엑셀·JSONL 내보내기) |
| E(손희영) — 시각화·리포트 | `dashboard.py` | 차트 4종(감정 분포· 5일 단위 시간별 감정 추이·별점×감정·제품별 평균 별점) + 종합 Markdown 리포트 생성 |

**진행 방식**: 각자 자기 파일만 수정하는 1인 1파일 원칙으로 작업했고, B~E가 파일을 완성해 GitHub에 올리면 A가 `main.py`에 실제로 연결하고 실행 테스트까지 마친 뒤 다시 커밋하는 흐름으로 통합했습니다. 저장소(`storage.py`)와 DB 스키마를 초반에 확정해 공유했기 때문에, 팀원들이 서로의 코드가 완성되기를 기다리지 않고 병렬로 작업할 수 있었습니다.

## 3. 기능 요약

### 3-1. 데이터 수집 및 저장 (`import`)
- CSV/엑셀 파일에서 리뷰(제품명, 별점, 작성일, 본문)를 읽어 `raw` 상태로 저장
- 텍스트(`text`)가 완전히 같으면 중복으로 판단, `config.json`의 `duplicate_policy`에 따라 skip(건너뜀) 또는 upsert(덮어쓰기) 처리
- CSV 인코딩(UTF-8 / CP949)을 자동 판별해서 읽음

### 3-2. 데이터 정제 (`clean`)
정제 규칙 5가지를 순서대로 적용하며, 각 단계에서 제외된 건은 원본을 지우지 않고 WARNING으로 로그만 남깁니다.
1. 필수 필드 검증 — 리뷰 본문(text)이 비어 있으면 제외
2. 텍스트 정규화 — 앞뒤 공백 제거, 연속 공백/줄바꿈을 한 칸으로 통일
3. 별점 범위 검증 — 1~5 범위를 벗어나거나 숫자가 아니면 제외
4. 날짜 형식 통일 — 다양한 표기를 `YYYY-MM-DD`로 통일, 해석 불가한 값은 제외
5. 짧은 리뷰 필터링 — 설정된 최소 글자 수(기본 10자) 미만이면 제외

`data/bad_reviews.csv`는 이 5가지 규칙이 실제로 걸러내는지 검증하기 위해 일부러 불량 데이터(별점 범위 초과, 빈 값, 잘못된 날짜 등)를 넣어 만든 테스트용 파일입니다.

### 3-3. AI 감정 분석 (`analyze`)
- OpenAI API를 호출해 리뷰별 감정(positive/negative/neutral)과 신뢰도 점수(0.0~1.0)를 분석
- 분석 대상 텍스트는 정제된 텍스트(`text_clean`)를 우선 사용하고, 비어 있으면 원문(`text`)으로 대체
- `--all`(전체 재분석) / `--id`(특정 건) / `--unanalyzed`(미분석 건만, 기본값) 옵션 지원
- API 통신 오류나 응답 형식 오류가 나면 해당 건만 로깅 후 건너뛰고 나머지는 계속 진행

### 3-4. AI 키워드·요약 추출 (`extract`)
- 조건(감정/제품/기간)에 맞는 리뷰를 최대 30건까지 모아 한 번에 AI에 요청 (정제된 텍스트 우선 사용)
- 키워드, 전체 요약, 개선 제안을 추출해 저장

### 3-5. 데이터 조회 (`list` / `show` / `stats`)
- `list`: 감정·별점·기간 필터, `--sort`(날짜/별점) 정렬, 페이지네이션
- `show`: 리뷰 1건의 원문과 분석 결과 상세 조회
- `stats`: 정제(clean) 통과 리뷰 기준 총 리뷰 수, 감정별 비율, 별점 분포, 평균 별점, 평균 감정 점수

### 3-6. 시각화 및 리포트 (`dashboard`)
- 차트 4종(요구사항 3종 + 제품별 평균 별점 추가): 감정 분포, 시간별 감정 추이, 별점별 감정 분포, 제품별 평균 별점
- 5일 단위 시간별 감정 추이는 일별 변동을 완화하고 전체 흐름을 보기 쉽도록 리뷰를 5일 단위로 집계해 시각화
- 한글 폰트를 OS별로 자동 탐색해 적용 (macOS: AppleGothic, Windows: Malgun Gothic 등)
- 종합 리포트: 품질 지표(분석 완료율, 평균 감정 신뢰도 등), TOP 3 제품, AI 추출 결과를 콘솔 출력 + `output/review_report.md` 파일로 저장

> **참고**: `dashboard`는 `extract`를 한 번 이상 실행한 뒤에 돌려야 합니다. AI 추출 결과가 전혀 없는 상태에서 실행하면 리포트 생성 단계에서 오류가 발생해 `review_report.md` 파일 자체가 생성되지 않습니다 (차트 4종은 이 경우에도 정상 생성됩니다). 알려진 이슈이며, 정해진 실행 순서(`extract` → `dashboard`)를 지키면 문제없이 동작합니다.

### 3-7. 데이터 내보내기 (`export`)
- CSV(`utf-8-sig`, 엑셀에서 한글 안 깨짐), 엑셀, JSONL 3개 포맷 지원
- `--sentiment`, `--rating-min` 필터 지원

### 3-8. 설정 및 로깅
- `config.json`(API 키, 중복 정책, 폰트 이름 등)으로 설정 관리, API 키는 코드에 직접 작성하지 않음
- `logging` 모듈로 INFO/WARNING/ERROR 로그를 `app.log` 파일과 콘솔에 동시 기록

## 4. 설치 및 실행 방법

### 4-1. 설치
```bash
pip install -r requirements.txt
```

### 4-2. API 키 설정
1. `config.example.json`을 복사해 `config.json`을 만듭니다.
2. 발급받은 OpenAI API 키를 `config.json`의 `api_key` 항목에 입력합니다.
3. `config.json`은 `.gitignore`에 포함되어 있어 GitHub에 올라가지 않습니다.

### 4-3. 실행 순서
```bash
python3 main.py import --file data/sample_reviews.csv
python3 main.py clean
python3 main.py analyze --unanalyzed
python3 main.py extract --sentiment negative
python3 main.py stats
python3 main.py list --sentiment negative
python3 main.py show --id 1
python3 main.py dashboard
python3 main.py export --format csv
```

### 4-4. 전체 명령어 옵션
| 명령어 | 주요 옵션 |
|---|---|
| `import` | `--file` (필수) |
| `clean` | (옵션 없음) |
| `analyze` | `--all`, `--id`, `--unanalyzed`, `--limit` |
| `extract` | `--sentiment`, `--product`, `--date-from`, `--date-to` |
| `list` | `--sentiment`, `--rating`, `--date-from`, `--date-to`, `--page`, `--size`, `--sort` |
| `show` | `--id` (필수) |
| `stats` | (옵션 없음) |
| `dashboard` | (옵션 없음) |
| `export` | `--format` (csv/excel/jsonl), `--sentiment`, `--rating-min` |

## 5. 생성 결과물

`dashboard` 및 `export` 실행 시 `output/` 폴더에 아래 파일들이 생성됩니다.

```
output/
├── sentiment_distribution.png       # 감정 분포
├── sentiment_time_trend.png         # 5일 단위 시간별 감정 추이
├── rating_sentiment_distribution.png # 별점별 감정 분포
├── product_average_rating.png       # 제품별 평균 별점
├── review_report.md                 # 종합 분석 리포트
└── export_<날짜시간>.<csv|xlsx|jsonl>  # 내보내기 결과
```

## 6. 데이터베이스 구조

SQLite(`reviews.db`)에 테이블 2개를 사용합니다.

- **reviews**: id, product, rating, review_date, text, text_clean, status(raw/clean), sentiment, score, analyzed_at, created_at
- **extractions**: id, condition_desc, keywords, summary, suggestions, created_at

## 7. 샘플 데이터

- `data/sample_reviews.csv`: 정상 리뷰 샘플 데이터(약 40건, 중복 제거 후 clean 38건)
- `data/bad_reviews.csv`: 정제 규칙 검증용 불량 데이터 (별점 범위 초과, 빈 값, 잘못된 날짜 등 포함)
