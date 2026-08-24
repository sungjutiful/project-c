"""
analyzer.py — C 담당
analyze: 리뷰별 감정 + 점수 분석 (AI API 호출, storage.update_sentiment 사용)
extract: 키워드·요약·개선 제안 추출 (storage.insert_extraction 사용)
"""
# C가 여기 채우기

import os
import json
import logging
import openai

# 로깅 기본 설정
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# API 키 설정 (config.json 또는 환경변수 연동 필요)
openai.api_key = os.getenv("OPENAI_API_KEY", "")


def get_sentiment_prompt(review_text):
    """
    리뷰 텍스트를 기반으로 AI 감정 분석 프롬프트를 생성합니다.
    """
    prompt = f"""당신은 고객 리뷰 감정 분석 전문가입니다.
아래 고객 리뷰를 읽고 긍정(positive), 부정(negative), 중립(neutral) 중 하나의 감정으로 분류하고, 확신도 점수(0.0 ~ 1.0)를 측정하세요.

[절대 규칙]
1. 반드시 아래 JSON 형식으로만 응답할 것.
2. 마크다운 기호(```json 등)나 기타 설명문은 절대 포함하지 말 것.

[출력 형식]
{{"sentiment": "positive", "score": 0.9}}

[고객 리뷰]
"{review_text}"
"""
    return prompt


def analyze_reviews(reviews_data, unanalyzed_only=True, limit=None):
    """
    OpenAI API를 활용한 리뷰 감정 분석 수행
    
    :param reviews_data: 분석 대상 리뷰 리스트 (dict)
    :param unanalyzed_only: True일 경우 이미 감정 분석이 완료된 리뷰는 스킵
    :param limit: 분석할 최대 리뷰 건수 제한 (API 비용 관리 목적)
    :return: 분석이 완료된 결과 리스트
    """
    logging.info(f"감정 분석 모듈을 시작합니다. (입력 데이터: {len(reviews_data)}건)")
    
    results = []
    processed_count = 0
    
    for review in reviews_data:
        # Limit 도달 시 즉시 루프 종료
        if limit and processed_count >= limit:
            logging.info(f"지정된 최대 처리 건수({limit}건)에 도달하여 분석을 종료합니다.")
            break
            
        review_id = review.get('id')
        text = review.get('text')
        
        # 기분석 데이터 스킵 로직 (Idempotency 처리)
        if unanalyzed_only and review.get('sentiment') and review.get('score') is not None:
            logging.info(f"Review ID [{review_id}] 이미 분석된 리뷰입니다. 스킵합니다.")
            continue
            
        logging.info(f"Review ID [{review_id}] 분석 진행 중...")
        
        try:
            prompt = get_sentiment_prompt(text)
            
            # API 호출 (temperature=0.0으로 일관성 강제)
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0 
            )
            
            ai_answer = response.choices[0].message.content.strip()
            
            # JSON 파싱 및 데이터 추출
            try:
                parsed_data = json.loads(ai_answer)
                sentiment = parsed_data.get('sentiment')
                score = parsed_data.get('score')
                
                logging.info(f" -> 분석 완료: {sentiment} (score: {score})")
                
                results.append({
                    'id': review_id,
                    'sentiment': sentiment,
                    'score': score
                })
                processed_count += 1
                
            except json.JSONDecodeError:
                logging.error(f" -> JSON 파싱 에러 (Review ID: {review_id}). 응답을 스킵합니다.")
                continue
                
        except Exception as e:
            logging.error(f" -> API 통신 에러 발생 (Review ID: {review_id}): {e}")
            continue
            
    logging.info(f"감정 분석 처리가 모두 완료되었습니다. (총 {processed_count}건 처리)")
    return results


if __name__ == "__main__":
    # 단독 모듈 테스트용 샘플 데이터 (팀원 B의 DB 스키마 형태 가정)
    sample_db_reviews = [
        {'id': 1, 'text': '정말 최악입니다. 포장이 다 뜯어져서 왔어요.', 'sentiment': None, 'score': None},
        {'id': 2, 'text': '가성비 최고! 디자인도 마음에 쏙 듭니다.', 'sentiment': 'positive', 'score': 0.95}, # 기분석 데이터
        {'id': 3, 'text': '그냥저냥 쓸만해요. 배송은 보통.', 'sentiment': None, 'score': None},
        {'id': 4, 'text': '재구매 의사 있습니다. 좋아요.', 'sentiment': None, 'score': None}
    ]
    
    # 실제 테스트 시 아래 주석 해제 및 API 키 세팅 후 실행
    # limit=2를 통해 최대 2건만 분석, unanalyzed_only=True로 ID 2번은 자동 스킵됨
    # analyze_reviews(sample_db_reviews, unanalyzed_only=True, limit=2)
