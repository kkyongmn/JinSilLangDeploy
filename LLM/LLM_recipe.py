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
import sys

# refrigeratordb 寃쎈줈 異붽��
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database'))
import refrigeratordb

# �솚寃� 蹂��닔 濡쒕뱶
load_dotenv()

# OpenAI �겢�씪�씠�뼵�듃 �씤�뒪�꽩�뒪 �깮�꽦
client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

# �꽕�씠踰� API �궎 �꽕�젙
NAVER_CLIENT_ID = Config.NAVER_CLIENT_ID
NAVER_CLIENT_SECRET = Config.NAVER_CLIENT_SECRET


# test_top.py�뿉�꽌 �쓬�떇 諛� �옱猷� �젙蹂� 媛��졇�삤湲�
def load_top_k_items(k, db_path):
    top_k_items = refrigeratordb.get_top_k_items(k, db_path)
    items = [item['name'] for item in top_k_items]
    print(f"items: {items}")
    return items

# �꽕�씠踰� API�뿉�꽌 �뜲�씠�꽣 媛��졇�삤�뒗 �븿�닔
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

# 二쇱슂 �옱猷뚮굹 �슂由� �씠由꾩쓣 GPT-4瑜� �넻�빐 異붿텧�븯�뒗 �븿�닔
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

# �젅�떆�뵾 �젙蹂대�� 媛��졇�삤�뒗 �븿�닔
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

    #image_tag = soup.find('div', class_='centeredcrop').find('img')
    #img_url = image_tag['src'] if image_tag else None

    ingredient_tags = soup.select('div.ready_ingre3 ul li')
    ingredients = ', '.join(tag.get_text(strip=True) for tag in ingredient_tags)

    step_tags = soup.select('div.view_step_cont')
    steps = [f"{i+1}. {step.get_text(strip=True)}" for i, step in enumerate(step_tags)]

    # 5. Return the collected data
    return {
        'name': title,
        'ingredients': ingredients,
        'recipe': steps,
        'recipe_url': f"{base_url}/recipe/{food_id}",
        # 'img': img_url,
    }

# DALL-E API瑜� �궗�슜
#def generate_food_image(food_name):
    # �봽濡ы봽�듃 
    prompt = (
        f"A hyper-realistic, high-resolution photo of {food_name} freshly prepared and served. "
        f"The dish should appear as if it was lovingly made at home, showcasing a cozy and authentic homemade feel. "
        f"Natural lighting enhances the texture and color of the ingredients, emphasizing the warmth and authenticity of the dish. "
        f"The presentation should be simple yet appetizing, avoiding overly stylized arrangements. "
        f"The setting includes a casual dining or kitchen environment, with subtle background elements like mismatched plates, wooden tables, "
        f"and everyday utensils that evoke the comforting atmosphere of a real home meal."
    )



    try:
        # DALL-E API �샇異�
        response = client.images.generate(
            model = "dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        # �깮�꽦�맂 �씠誘몄�� URL 諛섑솚
        return response.data[0].url
    except Exception as e:
        print(f"Error generating image: {e}")
        return None

# �궗�슜�옄 吏덈Ц�뿉 ����븳 �떟蹂� �깮�꽦
def get_answer_recipe(query):
    if isinstance(query, list):
        query = ", ".join(query)
        query = query + "�슂由� 諛⑸쾿 �븣�젮二쇱꽭�슂."
    keywords = extract_key_ingredient_gpt(query)
    print("Extracted keywords:", keywords)

    naver_data = fetch_naver_data(keywords, "food")
    if not naver_data:
        return "Sorry, I couldn't retrieve information from Naver."

    recipe_data = recipe_info(keywords)


    # GPT-4 紐⑤뜽�쓣 �넻�빐 理쒖쥌 �떟蹂� �깮�꽦
    answer = generate_response_with_gpt4(query, naver_data, recipe_data)
    return {
        "answer": answer,
        "keywords": keywords,
        "recipe_url": recipe_data.get("recipe_url", "")  # URL 포함

    }

# Few-shot example 
few_shot_example_1 = (
            "고추장 찌개 레시피를 알려드릴게요. 다음은 참치와 감자를 넣은 고추장 찌개의 기본적인 레시피입니다:\n\n"
            "### 재료:\n"
            "- 참치캔 1개\n"
            "- 감자 1개\n"
            "- 양파 1/2개\n"
            "- 두부 1/4모\n"
            "- 대파 1/2뿌리\n"
            "- 청양고추 1개\n"
            "- 물 2컵\n"
            "- 고추장 2.5큰술\n"
            "- 고춧가루 1큰술\n"
            "- 간장 1큰술\n"
            "- 다진 마늘 1/2큰술\n"
            "- 소금 1티스푼\n\n"
            "### 조리 방법:\n"
            "1. 참치는 기름기를 빼줍니다.\n"
            "2. 감자, 양파, 대파, 두부는 깍둑썰기하고 청양고추와 대파는 잘게 썰어줍니다.\n"
            "3. 물 2컵에 고추장, 간장, 다진 마늘을 넣어 잘 풀어줍니다.\n"
            "4. 감자, 양파, 참치, 고춧가루를 넣어 감자가 익을 때까지 끓여줍니다.\n"
            "5. 두부, 대파, 청양고추를 넣은 뒤 간을 보아 부족한 간은 소금으로 맞춰줍니다.\n"
            "6. 한 번 더 끓여주어 완성합니다.\n\n"
            "좀 더 자세한 레시피는 [여기](https://www.10000recipe.com/recipe/6858055)에서 확인하실 수 있습니다. 맛있게 요리하세요!"
)

# GPT-4 紐⑤뜽�쓣 �넻�빐 �떟蹂� �깮�꽦�븯�뒗 �븿�닔
def generate_response_with_gpt4(prompt, naver_data, recipe_data):
    naver_info = "\n".join([item['description'] for item in naver_data['items']])
    
    recipe_info_str = (
        f"Recipe Name: {recipe_data['name']}\n"
        f"Ingredients: {recipe_data['ingredients']}\n"
        f"Steps:\n" + "\n".join(recipe_data['recipe']) +
        f"\nRecipe URL: {recipe_data['url']}" if recipe_data else "No recipe information found."
    )
    gpt_prompt = (
        f"User's question: {prompt}\n\n"
        f"Naver Encyclopedia information:\n{naver_info}\n\n"
        f"Recipe information:\n{recipe_info_str}\n\n"
        "Generate a helpful and informative recipe response using all the provided information."
        "If a recipe link from '만개의 레시피' is available, make sure to include the link in the response."
        "Please write the answer in Korean"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a knowledgeable assistant specialized in food and health."},
            {"role": "assistant", "content": few_shot_example_1},
            {"role": "user", "content": gpt_prompt},
        ]
    )

    return response.choices[0].message.content

# 硫붿씤 �븿�닔
if __name__ == "__main__":
    # �뀒�뒪�듃 �뜲�씠�꽣踰좎씠�뒪 寃쎈줈 �꽕�젙
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database', 'refrigerator.db')
    # �쓬�떇 諛� �옱猷� �젙蹂� 濡쒕뱶
    top_k_items = load_top_k_items(5, db_path)    
    # �떟蹂� �깮�꽦 諛� 異쒕젰
    response = get_answer_recipe(top_k_items)
    print(response.get("answer"))
    test_food_name = "김치찌개"
    #image_url = generate_food_image(test_food_name)

    # # recipe_data 객체를 생성하여 URL을 설정
    # recipe_data = {
    #     'url': recipe_info.get('url', '')  # recipe_info에서 URL을 추출하여 recipe_data에 할당
    # }
    # DALL-E �씠誘몄�� URL �뿴湲�)
    #print(f"Generated Image URL for {test_food_name}: {image_url}")
    # print(f"Recipe URL: {recipe_data['url']}")
    print(response.get("recipe_url"))
    recipe_url = response.get("recipe_url")
