import os
import sqlite3
import json
import refrigeratordb

# 테스트용 DB 설정 (테스트 환경에 맞게 경로를 수정하세요)
# 절대 경로로 수정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 현재 파일의 디렉토리 경로
DB_PATH = os.path.join(BASE_DIR, "refrigerator.db")

DB_PATH2 = "refrigerator.db"

# 데이터 확인
def check_data():
    conn = sqlite3.connect(DB_PATH2)
    cursor = conn.cursor()
    
    # 테이블 목록 확인
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print("Tables:", cursor.fetchall())

    # foods 테이블 데이터 확인
    cursor.execute("SELECT * FROM foods;")
    rows = cursor.fetchall()
    conn.close()

    if rows:
        print("Foods data:")
        for row in rows:
            print(row)
    else:
        print("No data in 'foods' table.")

check_data()


if __name__ == "__main__":
    # k가 데이터베이스에 있는 음식 수보다 큰 경우 테스트
    k = 15  # 상위 3개의 데이터를 가져오기
    top_k_items = refrigeratordb.get_top_k_items(k, DB_PATH)
    print(f"Top {k} items with nearest expiry (or all available):")
    for item in top_k_items:
        print(item)

    # JSON 결과 확인
    with open("top_k_expiry_items.json", "r") as json_file:
        saved_data = json.load(json_file)
        print("\nSaved JSON data:")
        print(json.dumps(saved_data, indent=4))
