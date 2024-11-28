import os
import openai
import json
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from config import Config
from langchain_openai import OpenAIEmbeddings, OpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
import sys
import re
import random

# refrigeratordb 경로 추가
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database'))
import refrigeratordb

# 환경 변수 로드
load_dotenv()

# OpenAI 클라이언트 인스턴스 생성
client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

# 네이버 API 키 설정
NAVER_CLIENT_ID = Config.NAVER_CLIENT_ID
NAVER_CLIENT_SECRET = Config.NAVER_CLIENT_SECRET

# OpenAI 임베딩 설정
embedding = OpenAIEmbeddings(openai_api_key=Config.OPENAI_API_KEY)

# test_top.py에서 음식 및 재료 정보 가져오기
def load_top_k_items(k, db_path):
    top_k_items = refrigeratordb.get_top_k_items(k, db_path)
    items = [item['name'] for item in top_k_items]
    print(f"items: {items}")
    return items

# JSON 파일에서 음식 보관 정보 로드
def load_storage_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

# JSON 데이터를 벡터 스토어에 임베딩 및 저장
def create_vector_store(data):
    texts = []
    metadatas = []
    for category in data:
        for item in category.get('subcategories', []):
            food_name = item['food']
            for method in item['storage_method']:
                text = f"{food_name} - {method['condition']}: {method['description']}"
                texts.append(text)
                metadatas.append({
                    "food": food_name,
                    "condition": method['condition'],
                    "type": method['type'],
                    "temperature": method['temperature'],
                    "description": method['description']
                })

    # 임베딩을 사용해 벡터 스토어 생성
    vector_store = FAISS.from_texts(texts, embedding, metadatas=metadatas)
    return vector_store

# 
# 사용자 질문에 대한 답변 생성
def get_answer_quiz(query, vector_store):
    """
    사용자 질문에 대한 퀴즈 생성 및 결과 반환
    """
    # 사용자 질문이 리스트인 경우 첫 번째 요소를 사용하도록 함
    if isinstance(query, list):
        query = random.choice(query) + " 보관방법"
    else:
        query = query + " 보관방법"
    
    print(f"query: {query}")

    # 벡터 스토어를 통해 보관 정보 검색
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 2})
    llm = OpenAI(openai_api_key=Config.OPENAI_API_KEY)  # OpenAI 인스턴스 생성 시 API 키 전달
    qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)
    storage_info = qa_chain.invoke(query)
    print(f"storage_info: {storage_info}")

    # GPT-4 모델을 통해 퀴즈 생성
    quiz_data = generate_quiz_with_gpt4(query, storage_info)  # [질문, 답변, 해설] 반환

    # 리스트를 반환하도록 수정
    question = quiz_data[0] if len(quiz_data) > 0 else "질문 없음"
    answer = quiz_data[1] if len(quiz_data) > 1 else "답변 없음"
    explanation = quiz_data[2] if len(quiz_data) > 2 else "해설 없음"

    print(f"Question: {question}")
    print(f"Answer: {answer}")
    print(f"Explanation: {explanation}")

    # 세 가지 데이터를 리스트로 반환
    return [question, answer, explanation]

# Few-shot example 
few_shot_example_1 = (
    "Question: 전체 곡물 음식은 항상 지방이 적고 식이섬유의 원천입니다.\n"
    "Answer: X\n"
    "Explanation: 전체 곡물은 건강에 좋은 식이섬유의 원천입니다. 그러나, 항상 지방이 적은 것은 아닙니다. "
    "일부 곡물 제품은 가공 과정에서 지방, 설탕, 그리고 소금이 추가 될 수 있어, 이러한 영양소의 양이 더욱 늘어날 수 있습니다. "
    "따라서 영양 성분 표시를 확인하는 것이 중요합니다."
)

few_shot_example_2 = (
    "Question: 마요네즈는 개봉 전에도 냉장보관해야 한다.\n"
    "Answer: X\n"
    "Explanation: 마요네즈는 개봉 전에는 서늘하고 건조한 곳에서 보관해야 합니다. 개봉 후에는 냉장고에 보관하면 됩니다."
)


# GPT-4 모델을 통해 퀴즈 생성하는 함수
def generate_quiz_with_gpt4(items, storage_data):
    """
    GPT-4를 통해 퀴즈를 생성하고 [질문, 정답, 해설] 형태로 반환.
    """
    number = random.choice(range(0, 5))
    number = number % 2
    if number == 0:  # 60%의 확률
        prompt = (
            f"The following is a list of food items or ingredients: {items}.\n"
            f"Storage information:\n{storage_data}\n"
            "Generate one quiz question based on these items, providing both the question, the explanation, "
            "and whether the statement in the question is true or false. The format should be:\n"
            "Question: <question>\n"
            "Explanation: <explanation>\n"
            "Answer: <O or X>\n"
            "The question, explanation, and answer should be written in Korean."
        )
    else:
        prompt = (
            f"The following is a list of food items or ingredients: {items}.\n"
            f"Storage information:\n{storage_data}\n"
            "Generate one quiz question based on these items, providing both the question, the explanation, "
            "and whether the statement in the question is true or false. The format should be:\n"
            "Question: <question>\n"
            "Explanation: <explanation>\n"
            "Answer: <O or X>\n"
            "The question, explanation, and answer should be written in Korean."
        )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a quiz master specialized in food and ingredients."},
            {"role": "assistant", "content": few_shot_example_1},
            {"role": "assistant", "content": few_shot_example_2},
            {"role": "user", "content": prompt},
        ]
    )

    # GPT 응답에서 질문, 정답, 해설 추출
    result = response.choices[0].message.content.strip()
    question_match = re.search(r"Question:\s*(.*)", result)
    answer_match = re.search(r"Answer:\s*(O|X)", result, re.IGNORECASE)
    explanation_match = re.search(r"Explanation:\s*(.*)", result)

# 만약 텍스트가 영어라면 -> 이 함수 진행하면 좋겠음
#     # 번역 처리
#     translated_question = translate_to_korean(question.group(1).strip()) if question else "질문 없음"
#     translated_explanation = translate_to_korean(explanation.group(1).strip()) if explanation else "해설 없음"
    question = question_match.group(1) if question_match else "질문 없음"
    answer = answer_match.group(1) if answer_match else "답변 없음"
    explanation = explanation_match.group(1) if explanation_match else "해설 없음"
    # 번역된 질문, 정답, 해설 리스트 반환
    return [
        question,
        answer,
        explanation
    ]
## 예외 처리
def translate_to_korean(text):
    """
    OpenAI API를 사용하여 주어진 텍스트를 한국어로 번역.
    """
    prompt = (
        f"Translate the following text to Korean:\n"
        f"{text}"
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a professional translator."},
            {"role": "user", "content": prompt},
        ]
    )
    return response.choices[0].message.content.strip()




# 메인 함수
if __name__ == "__main__":
    # 테스트 데이터베이스 경로 설정
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database', 'refrigerator.db')
    # 음식 및 재료 정보 로드
    top_k_items = load_top_k_items(15, db_path)    
    # JSON 파일 경로 설정
    json_path = os.path.join(os.path.dirname(__file__), 'store_data.json')
    # 음식 보관 정보 로드
    storage_data = load_storage_data(json_path)
    # 벡터 스토어 생성
    vector_store = create_vector_store(storage_data)

    # 퀴즈 생성 및 출력
    quiz = get_answer_quiz(top_k_items, vector_store)
    print(quiz)
