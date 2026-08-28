"""
analyzer.py — C 담당
analyze: 리뷰별 감정 + 점수 분석 (AI API 호출, storage.update_sentiment 사용)
extract: 키워드·요약·개선 제안 추출 (storage.insert_extraction 사용)
"""
# C가 여기 채우기


import json
import logging
import os
import openai

# 로깅 기본 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] %(message)s')

# 설정 파일에서 API 키 로드
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        openai.api_key = config.get("api_key", "")
except FileNotFoundError:
    logging.warning("config.json 파일을 찾을 수 없습니다. 환경 변수를 확인합니다.")
    openai.api_key = os.getenv("OPENAI_API_KEY", "")


def get_sentiment_prompt(review_text: str) -> str:
    """
    단일 리뷰 감정 분석을 위한 프롬프트 생성
    """
    return f"""Analyze the sentiment of the following customer review.
Classify it as one of: positive, negative, or neutral. Also provide a confidence score between 0.0 and 1.0.

[Constraints]
1. Output strictly in JSON format.
2. Do not include markdown formatting or any additional text.

[Format]
{{"sentiment": "positive", "score": 0.9}}

[Review]
"{review_text}"
"""


def analyze_reviews(reviews_data: list, unanalyzed_only: bool = True, limit: int = None) -> list:
    """
    리뷰 데이터에 대한 감정 분석 수행 (OpenAI API 연동)
    """
    if not reviews_data:
        return []

    logging.info(f"감정 분석 프로세스 시작 (총 입력: {len(reviews_data)}건)")
    results = []
    processed_count = 0
    
    for review in reviews_data:
        if limit and processed_count >= limit:
            logging.info(f"처리 제한({limit}건) 도달. 분석을 중단합니다.")
            break
            
        review_id = review.get('id')
        
        # [수정됨] 정제된 텍스트(text_clean)를 우선 사용하고, 없으면 원문(text) 사용
        text = review.get('text_clean') or review.get('text')
        
        if not text:
            continue
            
        if unanalyzed_only and review.get('sentiment') and review.get('score') is not None:
            continue
            
        try:
            prompt = get_sentiment_prompt(text)
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0 
            )
            
            ai_answer = response.choices[0].message.content.strip()
            
            try:
                parsed_data = json.loads(ai_answer)
                sentiment = parsed_data.get('sentiment')
                score = parsed_data.get('score')
                
                logging.info(f"분석 성공 - ID: {review_id} | Sentiment: {sentiment} | Score: {score}")
                
                results.append({
                    'id': review_id,
                    'sentiment': sentiment,
                    'score': score
                })
                processed_count += 1
                
            except json.JSONDecodeError:
                logging.error(f"JSON 디코딩 에러 (Review ID: {review_id})")
                continue
                
        except Exception as e:
            logging.error(f"API 통신 에러 (Review ID: {review_id}): {str(e)}")
            continue
            
    logging.info(f"감정 분석 처리 완료 (총 처리 건수: {processed_count}건)")
    return results


def get_extraction_prompt(combined_texts: str) -> str:
    """
    다중 리뷰 종합 인사이트 추출을 위한 프롬프트 생성
    """
    return f"""Analyze the provided customer reviews and extract key insights.
Output strictly in the specified JSON format.

[Constraints]
1. Output strictly in JSON format.
2. Do not include markdown formatting or any additional text.

[Format]
{{
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "summary": "리뷰들의 핵심 내용 3줄 요약",
    "suggestions": "비즈니스 개선을 위한 실질적인 제안 2가지"
}}

[Reviews]
{combined_texts}
"""


def extract_insights(reviews_data: list, target_condition: str = "custom") -> dict:
    """
    조건별 리뷰 리스트를 종합하여 키워드 및 인사이트 추출
    """
    if not reviews_data:
        logging.warning("추출할 리뷰 데이터가 존재하지 않습니다.")
        return None
        
    logging.info(f"인사이트 추출 시작 (Target: {target_condition}, 데이터: {len(reviews_data)}건)")
    
    # [수정됨] 정제된 텍스트(text_clean)를 우선 사용하도록 수정
    combined_texts = "\n".join([f"Review {i+1}: {rev.get('text_clean') or rev.get('text')}" for i, rev in enumerate(reviews_data) if (rev.get('text_clean') or rev.get('text'))])
    
    try:
        prompt = get_extraction_prompt(combined_texts)
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3 
        )
        
        ai_answer = response.choices[0].message.content.strip()
        
        try:
            parsed_data = json.loads(ai_answer)
            parsed_data['target'] = target_condition
            logging.info(f"인사이트 추출 성공 (Target: {target_condition})")
            return parsed_data
            
        except json.JSONDecodeError:
            logging.error("인사이트 추출 결과 JSON 디코딩 에러 발생")
            return None
            
    except Exception as e:
        logging.error(f"인사이트 추출 API 통신 에러: {str(e)}")
        return None
