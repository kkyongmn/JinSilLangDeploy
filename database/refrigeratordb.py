from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
import os
import json

app = Flask(__name__)

# Database setup
DATABASE = 'refrigerator.db'

# database 폴더로 이동하는 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # Demo의 상위 폴더
DB_PATH = os.path.join(BASE_DIR, 'database', DATABASE)

# Initialize the database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            remaining_days INTEGER
        )
    ''')
    conn.commit()
    conn.close()
    
def calculate_remaining_days(expiry_date):
    today = datetime.today()
    expiry = datetime.strptime(expiry_date, "%Y-%m-%d")
    delta = (expiry - today).days + 1
    return max(delta, 0)  # 음수가 되지 않도록 0으로 설정    
    
def get_all_foods(db_path=DB_PATH):
    """
    데이터베이스에서 모든 음식 데이터를 가져오며 JSON으로 변환 가능한 형식으로 반환. remaining_days 오름차순으로 정렬
    """
    conn = sqlite3.connect(db_path)  # 데이터베이스 경로
    cursor = conn.cursor()

    # 데이터베이스에서 데이터 가져오기
    cursor.execute("""
        SELECT id, name, expiry_date
        FROM foods
        ORDER BY expiry_date ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    # JSON 변환 및 name/expiry_date 분리
    parsed_rows = []
    for row in rows:
        try:
            # name과 expiry_date가 JSON 형식이면 파싱
            name_data = json.loads(row[1])
            expiry_date_str = json.loads(row[2]).get("expiry", "알 수 없음")
            name = name_data.get("name", "알 수 없음")
        except (json.JSONDecodeError, TypeError):
            # JSON 파싱 실패 시 원래 값을 사용
            name = row[1]
            expiry_date_str = row[2]

        # expiry_date를 datetime 형식으로 변환
        try:
            expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
            remaining_days = (expiry_date - datetime.now()).days + 1
            remaining_days = max(remaining_days, 0)  # 음수 방지
        except ValueError:
            expiry_date = expiry_date_str  # 변환 실패 시 원래 값을 유지
            remaining_days = "정보 없음"

        parsed_rows.append({
            "id": row[0],
            "name": name,
            "expiry_date": expiry_date_str,  # 문자열로 저장
            "remaining_days": remaining_days
        })

    return parsed_rows

# Add an item to the database
def add_food(name, expiry_date):
    """Adds a food item and its expiry date to the database."""
    try:
        connection = sqlite3.connect(DB_PATH)  # Replace with your database file
        cursor = connection.cursor()
        # Insert the food item into the database
        cursor.execute("INSERT INTO foods (name, expiry_date) VALUES (?, ?)", (name, expiry_date))
        connection.commit()
        connection.close()
        print(f"Added food: {name} with expiry: {expiry_date}")
    except Exception as e:
        print(f"Error adding food to database: {e}")
        
# delete food in refrigerator
def delete_food(food_id):
    """Deletes a food item from the database by its ID."""
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 음식 삭제 쿼리 실행
        cursor.execute("DELETE FROM foods WHERE id = ?", (food_id,))
        conn.commit()

        print(f"Deleted food with ID: {food_id}")
    except Exception as e:
        print(f"Error deleting food from database: {e}")
    finally:
        conn.close()
        
def get_near_expiry_items(n):
    """
    Fetch items with remaining_days <= n from the database.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 남은 기간이 3일 이하인 항목 가져오기
    cursor.execute("""
        SELECT id, name, expiry_date,
               CAST((julianday(expiry_date) - julianday('now')) AS INTEGER) AS remaining_days
        FROM foods
        WHERE (julianday(expiry_date) - julianday('now')) <= 3
          AND (julianday(expiry_date) - julianday('now')) >= 0
    """)
    rows = cursor.fetchall()
    conn.close()
    
    print("Debug - Rows fetched from DB:", rows)  # Debugging output

    # JSON 형식으로 변환
    return [{"id": row[0], "name": row[1], "expiry_date": row[2], "remaining_days": row[3]} for row in rows]     

def get_top_k_items(k, db_path=DB_PATH):
    """
    Fetch top k items with the shortest remaining expiry days from the database.
    If there are fewer than k items, return all available items.
    """
    rows = get_all_foods(db_path)

    top_k_items = sorted(rows, key=lambda x: x["remaining_days"])[:k]
    
    # Save to JSON file
    with open("top_k_expiry_items.json", "w") as json_file:
        json.dump(top_k_items, json_file, indent=4)

    return top_k_items

@app.route('/get-expiry-alert', methods=['GET'])
def get_expiry_alert():
    try:
        items = get_near_expiry_items(3)
        print("Debug - Filtered items:", items)  # Debugging output
        return jsonify({"success": True, "items": items}), 200
    except Exception as e:
        print("Debug - Error:", e)  # Debugging output
        return jsonify({"success": False, "error": str(e)}), 500
    
def get_all_recipes():
    connection = sqlite3.connect('refrigerator.db')
    cursor = connection.cursor()

    cursor.execute("SELECT name, ingredients, time, image FROM recipes")
    recipes = cursor.fetchall()

    result = []
    for recipe in recipes:
        result.append({
            "name": recipe[0],
            "ingredients": recipe[1].split(','),  # 재료를 리스트로 변환
            "time": recipe[2],
            "image": recipe[3]
        })
        
    connection.close()
    return result

# View all items in the database
@app.route('/view_items', methods=['GET'])
def view_items():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT name, expiry_date, remaining_days FROM foods')
    items = cursor.fetchall()
    conn.close()

    return jsonify([
        {'name': item[0], 'expiry_date': item[1], 'remaining_days': item[2]}
        for item in items
    ])

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
