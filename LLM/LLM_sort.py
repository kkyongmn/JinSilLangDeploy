import os
import openai
import json
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from config import Config
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI  # OpenAI 임포트
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
import sys
import re
import random

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from database import refrigeratordb

# 환경 변수 로드
load_dotenv()

# OpenAI 클라이언트 인스턴스 생성
client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

# 네이버 API 키 설정
NAVER_CLIENT_ID = Config.NAVER_CLIENT_ID
NAVER_CLIENT_SECRET = Config.NAVER_CLIENT_SECRET

# OpenAI 임베딩 설정
embedding = OpenAIEmbeddings(openai_api_key=Config.OPENAI_API_KEY)

def load_top_k_items(k, db_path):
    top_k_items = refrigeratordb.get_top_k_items(k, db_path)
    items = [item['name'] for item in top_k_items]
    print(f"items: {items}")
    return items

def load_storage_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

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

def translate_to_korean(text):
    """
    OpenAI API를 사용하여 주어진 텍스트를 한국어로 번역.
    """
    prompt = (
        f"Translate the following text to Korean:\n"
        f"{text}"
    )
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a professional translator."},
            {"role": "user", "content": prompt},
        ]
    )
    return response.choices[0].message.content.strip()

json_data = load_storage_data("store_data.json")  # 예: JSON 파일 경로
vector_store = create_vector_store(json_data)
def store_sort(query, vector_store):
    print(f"query: {query}")
    """
    LLM을 사용해 보관 방법을 분류하는 함수.
    
    Args:
        query (list): 사용자로부터 입력받은 냉장고 보관물 이름 목록.
        vector_store (VectorStore): 유사도 검색용 벡터 저장소.

    Returns:
        dict: 보관 방법별로 분류된 결과 리스트.
    """
    room_temp = []
    refrigerated = []
    frozen = []
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 2})
    llm = ChatOpenAI(openai_api_key=Config.OPENAI_API_KEY)
    qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)

    for item in query:
        print(f"Processing: {item}")
        storage_info = qa_chain.invoke({"query": f"{item}는 어떻게 보관해야 하나요? ('실온', '냉장', '냉동' 중 하나로 답변, 반드시 2글자로 답변하시오.)"})
        storage_method = storage_info['result'].strip()
        
        print(f"Item: {item}, Storage Method: {storage_method}")

        # 보관 방법에 따라 분류
        if storage_method == "실온":
            room_temp.append(item)
        elif storage_method == "냉장":
            refrigerated.append(item)
        elif storage_method == "냉동":
            frozen.append(item)
        else:
            print(f"Warning: Unknown storage method for {item}")

    # 결과 반환
    return {
        "실온": room_temp,
        "냉장": refrigerated,
        "냉동": frozen
    }


# 메인 함수
if __name__ == "__main__":
    all_foods = refrigeratordb.get_all_foods()  # 리스트나 딕셔너리를 반환해야 함
    if isinstance(all_foods, list):  # 리스트일 경우
        food_names = [food['name'] for food in all_foods]  # 'name' 키가 존재하는지 확인
        print(store_sort(food_names, vector_store))  # vector_store는 적절히 전달
    else:
        print("Error: get_all_foods() did not return a list")