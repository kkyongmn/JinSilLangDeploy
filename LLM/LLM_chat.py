import os
import requests
import openai
import json
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from config import Config
from langchain_openai import OpenAIEmbeddings, OpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
import re

# 환경 변수 로드
load_dotenv()

# OpenAI 클라이언트 인스턴스 생성
client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

# 네이버 API 키 설정
NAVER_CLIENT_ID = Config.NAVER_CLIENT_ID
NAVER_CLIENT_SECRET = Config.NAVER_CLIENT_SECRET

# USDA API 키 설정
FDC_API = os.getenv("FDC_API")

# OpenAI 임베딩 설정
embedding = OpenAIEmbeddings(openai_api_key=Config.OPENAI_API_KEY)

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

# 네이버 API에서 데이터 가져오는 함수
def fetch_naver_data(query, category='food'):
    url = f'https://openapi.naver.com/v1/search/encyc.json'
    headers = {
        'X-Naver-Client-Id': NAVER_CLIENT_ID,
        'X-Naver-Client-Secret': NAVER_CLIENT_SECRET,
    }

    params = {
        'query': query,
        'display': 5,
        'sort': 'sim'
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data from Naver API: {response.status_code}")
        return None

# USDA API에서 식품 성분 정보 가져오는 함수
def fetch_usda_food_data(query):
    url = 'https://api.nal.usda.gov/fdc/v1/foods/search'
    params = {
        'query': query,
        'pageSize': 2,  # 최대 2개의 결과를 가져옴
        'api_key': FDC_API
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data from USDA API: {response.status_code}")
        return None

# 주요 재료나 요리 이름을 GPT-4를 통해 추출하는 함수
def extract_key_ingredient_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an assistant that processes user input about food. "
                    "If the input contains ingredients, suggest a possible dish that can be made with those ingredients. "
                    "If the input is a dish name, return the name of the dish as is. "
                    "Return only the relevant result as a simple string without any additional text or formatting."
                )
            },
            {"role": "user", "content": prompt},
        ]
    )
    return response.choices[0].message.content.strip()

# 레시피 정보를 가져오는 함수
def recipe_info(food_name):
    base_url = "https://www.10000recipe.com"

    # 1. Food search request
    search_response = requests.get(f"{base_url}/recipe/list.html?q={food_name}")
    if search_response.status_code != 200:
        print("HTTP response error:", search_response.status_code)
        return

    # 2. Parse first food item ID from the search results
    soup = BeautifulSoup(search_response.text, 'html.parser')
    food_list = soup.find_all(attrs={'class': 'common_sp_link'})
    if not food_list:
        print("No recipes found.")
        return

    # 3. Get detailed recipe info using food ID
    food_id = food_list[0]['href'].split('/')[-1]
    recipe_response = requests.get(f"{base_url}/recipe/{food_id}")
    if recipe_response.status_code != 200:
        print("HTTP response error:", recipe_response.status_code)
        return

    # 4. Parse recipe details
    soup = BeautifulSoup(recipe_response.text, 'html.parser')
    title_tag = soup.find('div', class_='view2_summary')
    title = title_tag.find('h3').get_text(strip=True) if title_tag else "No Title"

    image_tag = soup.find('div', class_='centeredcrop').find('img')
    img_url = image_tag['src'] if image_tag else None

    ingredient_tags = soup.select('div.ready_ingre3 ul li')
    ingredients = ', '.join(tag.get_text(strip=True) for tag in ingredient_tags)

    step_tags = soup.select('div.view_step_cont')
    steps = [f"{i+1}. {step.get_text(strip=True)}" for i, step in enumerate(step_tags)]

    # 5. Return the collected data
    return {
        'name': title,
        'ingredients': ingredients,
        'recipe': steps,
        'url': f"{base_url}/recipe/{food_id}",
        'img': img_url,
    }

### 만약 영양성분을 물어보면 이걸 쓰는 것이 좋을듯 
# 키워드를 GPT-4를 통해 번역하는 함수
def translate_keywords_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a translator that helps translate Korean phrases into English."
                )
            },
            {"role": "user", "content": f"Translate the following Korean phrase into English: {prompt}"},
        ]
    )
    return response.choices[0].message.content.strip()

# 사용자 질문에 대한 답변 생성
def get_answer_chat(query, vector_store):
    keywords = extract_key_ingredient_gpt(query)
    print("Extracted keywords:", keywords)
    translated_query = translate_keywords_gpt(keywords)

    naver_data = fetch_naver_data(keywords, "food")
    if not naver_data:
        return "Sorry, I couldn't retrieve information from Naver."

    usda_data = fetch_usda_food_data(translated_query)

    recipe_data = recipe_info(keywords)

    # 벡터 스토어를 통해 보관 정보 검색
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 2})
    llm = OpenAI(openai_api_key=Config.OPENAI_API_KEY)  # OpenAI 인스턴스 생성 시 API 키 전달
    qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)
    storage_info = qa_chain.invoke(query)

    # GPT-4 모델을 통해 최종 답변 생성
    answer = generate_response_with_gpt4(query, naver_data, usda_data, recipe_data, storage_info)
    return answer

# GPT-4 모델을 통해 답변 생성하는 함수
def generate_response_with_gpt4(prompt, naver_data, usda_data, recipe_data, storage_data):
    naver_info = "\n".join([item['description'] for item in naver_data['items']])
    usda_info = "\n".join([
        f"Food: {food['description']}, Nutrients: " +
        ", ".join([f"{nutrient['nutrientName']}: {nutrient['value']} {nutrient['unitName']}" for nutrient in food.get('foodNutrients', [])])
        for food in usda_data['foods']
    ]) if usda_data and 'foods' in usda_data else "No relevant USDA information found."

    recipe_info_str = (
        f"Recipe Name: {recipe_data['name']}\n"
        f"Ingredients: {recipe_data['ingredients']}\n"
        f"Steps:\n" + "\n".join(recipe_data['recipe']) +
        f"\nRecipe URL: {recipe_data['url']}" if recipe_data else "No recipe information found."
    )

    gpt_prompt = (
        f"User's question: {prompt}\n\n"
        f"Naver Encyclopedia information:\n{naver_info}\n\n"
        f"USDA Food Data Central information:\n{usda_info}\n\n"
        f"Recipe information:\n{recipe_info_str}\n\n"
        f"Storage information:\n{storage_data}\n\n"
        "Generate a helpful and informative response using all the provided information."
        "If a recipe link from '만개의 레시피' is available, make sure to include the link in the response. "
        "Please write the question in Korean."
    )
##         "If a recipe link from '만개의 레시피' is available and relevant to the user's query, include the link in the response. "


    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a knowledgeable assistant specialized in food and health."},
            {"role": "user", "content": gpt_prompt},
        ]
    )

    return response.choices[0].message.content

# 메인 함수
if __name__ == "__main__":
    # JSON 파일 경로 설정
    json_path = os.path.join(os.path.dirname(__file__), 'store_data.json')
    # 음식 보관 정보 로드
    storage_data = load_storage_data(json_path)
    # 벡터 스토어 생성
    vector_store = create_vector_store(storage_data)
    # 사용자 질문 예시
    user_question = "간장, 계란, 버터로 만들 수 있는 음식 레시피 알려줘"
    # 답변 생성 및 출력
    response = get_answer_chat(user_question, vector_store)
    print(response)

