import sqlite3
import os

def initialize_database():
    # database 폴더 경로를 설정
    base_dir = os.path.dirname(__file__)  # 현재 파일 경로
    db_path = os.path.join(base_dir, '..', 'database', 'refrigeratordb.db')  # database 폴더로 이동

    # 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # foods 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS foods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        expiry_date DATE NOT NULL,
        remaining_days INTEGER
    )
    ''')

    # recipes 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        ingredients TEXT NOT NULL, -- 쉼표로 구분된 재료 목록
        time INTEGER NOT NULL, -- 요리 시간 (분)
        image TEXT -- 이미지 경로 또는 URL
    )
    ''')

    # 샘플 데이터 삽입 (recipes)
    sample_recipes = [
        ("감자 샐러드", "감자,마요네즈,양파", 20, "/static/Salad.png"),
        ("감자탕", "감자,돼지고기,대파,고추장", 60, "/static/Potato.jpeg"),
        ("볶음밥", "밥,계란,대파,간장", 15, "/static/FriedRice.png")
    ]

    for recipe in sample_recipes:
        cursor.execute("INSERT OR IGNORE INTO recipes (name, ingredients, time, image) VALUES (?, ?, ?, ?)", recipe)

    conn.commit()
    conn.close()
    print(f"Database initialized successfully at {db_path}!")

if __name__ == "__main__":
    initialize_database()
