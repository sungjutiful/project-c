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

