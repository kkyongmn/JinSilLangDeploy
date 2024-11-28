from flask import Flask, render_template, request, redirect, jsonify, url_for
from dotenv import load_dotenv
import os
import sys
import sqlite3
import requests
from config import Config
import re
import json
#from database.refrigeratordb import get_all_foods

# LLM_chat 모듈 가져오기

load_dotenv()

# 상위 디렉토리를 모듈 탐색 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'LLM'))

# DB_picture 
from LLM import DB_picture
# LLM_chat 모듈 가져오기
from LLM_chat import get_answer_chat, create_vector_store, load_storage_data
# LLM_quiz 모듈 가져오기
from LLM_quiz import get_answer_quiz, create_vector_store, load_top_k_items, load_storage_data
# LLM_recipe 모듈 가져오기
from LLM_recipe import get_answer_recipe, load_top_k_items, generate_food_image
# refrigeratordb 
from database import refrigeratordb

app = Flask(__name__)

# JSON 파일 경로 설정
json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'LLM', 'store_data.json')
sample_json_path_for_picture = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'LLM', 'top_k_expiry_items.json')
# JSON 파일 경로 설정
with open(sample_json_path_for_picture, 'r', encoding='utf-8') as f:
    top_k_items = json.load(f)

storage_data = load_storage_data(json_path)
vector_store = create_vector_store(storage_data)

refrigeratordb.init_db()

import openai
client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
# Configure OpenAI API

# JSON 
json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'LLM', 'store_data.json')# �쓬�떇 蹂닿�� �젙蹂� 濡쒕뱶 諛� 踰≫꽣 �뒪�넗�뼱 �깮�꽦
storage_data = load_storage_data(json_path)
vector_store = create_vector_store(storage_data)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/myFridge')
def my_fridge():
    try:
        food_list = refrigeratordb.get_all_foods()
        food_with_images = [
            {"food": food, "image_url": DB_picture.search_images(food["name"])}
            for food in food_list
        ]
        return render_template('myFridge.html', food_with_images=food_with_images)
    except sqlite3.OperationalError as e:
        return f"Database Error: {e}", 500
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/add-food-page')
def add_food_page():
    return render_template('addFood.html')

@app.route('/add_food', methods=['POST'])
def add_food():
    data = request.json
    name = request.get_data('name')
    expiry = request.get_data('expiry_date')
    
    if not name or not expiry:
        return jsonify({"success": False, "error": "紐⑤뱺 �븘�뱶瑜� �엯�젰�븯�꽭�슂."}), 400
    try:
        refrigeratordb.add_food(name, expiry)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/delete_food', methods=['POST'])
def delete_food_endpoint():
    food_id = request.json.get('food_id')
    if not food_id:
        return jsonify({"success": False, "error": "�쓬�떇 ID媛� �븘�슂�빀�땲�떎."}), 400

    try:
        refrigeratordb.delete_food(food_id)
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/get-items', methods=['GET'])
def get_items():
    try:
        items = refrigeratordb.get_all_foods()   # 모든 음식 데이터를 가져옴
        sorted_items = sorted(items, key=lambda x: x['remaining_days'])
        return jsonify({"foods": sorted_items, "success": True}), 200
    except Exception as e:
        return jsonify({"foods": [], "success": False, "error": str(e)}), 500

    
@app.route('/get-expiry-alert', methods=['GET'])
def get_expiry_alert():
    try:
        items = refrigeratordb.get_all_foods()
        filtered_items = [item for item in items if item['remaining_days'] <= 3]
        
        # JSON 
        return jsonify({"items": filtered_items, "success": True})
    except Exception as e:
        return jsonify({"items": [], "success": False, "error": str(e)})

@app.route('/quiz')
def quiz():
    try:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'refrigerator.db')
        top_k_items = load_top_k_items(15, db_path)

        quiz_data = get_answer_quiz(top_k_items, vector_store)

        return render_template(
            'quiz.html',
            question=quiz_data[0],
            answer=quiz_data[1],
            explanation=quiz_data[2]
        )
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/recipe')
def recipe():
    try:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'refrigerator.db')
        top_k_items = load_top_k_items(5, db_path)
        
        recipe_data = get_answer_recipe(top_k_items)

        
        food_name = recipe_data.get("keywords", "") 
        recipe_data = recipe_data.get("answer", "") 
        image_url = generate_food_image(food_name)  
        recipe_url = recipe_data.get("recipe_url", "")

        return render_template(
            'recipe.html',
            recipe_data=recipe_data,
            image_url=image_url,
            recipe_url = recipe_data.get("recipe_url", "")

        )

    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/get-recipes', methods=['GET'])
def get_recipes():
    try:

        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'refrigerator.db')
        top_k_items = load_top_k_items(5, db_path)
        recipe_data = get_answer_recipe(top_k_items)

        
        food_name = recipe_data.get("keywords", "")  
        recipe_data = recipe_data.get("answer", "")
        image_url = generate_food_image(food_name)  
        recipe_url = recipe_data.get("recipe_url", "")

        return render_template(
            'recipe.html',
            recipe_data = recipe_data,
            image_url=image_url,
            recipe_url = recipe_url
        )

    except Exception as e:
        return f"Error: {str(e)}", 500


# Route for chatbot.html
@app.route("/chatbot")
def chatbot_page():
    return render_template("chatbot.html")

# API endpoint for chatbot responses
@app.route("/get_response", methods=["POST"])
def get_response():
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"response": "Please send a message!"}), 400
    bot_response = get_answer_chat(user_message, vector_store)
    return jsonify({"response": bot_response})

if __name__ == "__main__":
    refrigeratordb.init_db()
    app.run(debug=True)
