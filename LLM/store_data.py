import json
import faiss
from openai import ChatCompletion
from sentence_transformers import SentenceTransformer

file_path = "store_data.json"

# JSON 데이터 읽기 및 변환
def json_to_rag_documents(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        
        documents = []
        for category in data:
            category_name = category["category"]
            for subcategory in category["subcategories"]:
                food_name = subcategory["food"]
                for method in subcategory["storage_method"]:
                    title = f"{category_name} - {food_name} ({method['condition']})"
                    content = (
                        f"{food_name}은/는 {method['condition']} 상태에서 "
                        f"{method['type']}({method['temperature']})로 보관해야 합니다. "
                        f"{method['description']}"
                    )
                    documents.append({"title": title, "content": content})
        return documents
    except FileNotFoundError:
        print(f"파일 '{file_path}'을(를) 찾을 수 없습니다.")
        return []
    except json.JSONDecodeError:
        print("JSON 파일을 읽는 중 오류가 발생했습니다.")
        return []

# 변환 실행
documents = json_to_rag_documents(file_path)
if not documents:
    print("문서를 읽어들이는데 실패했습니다.")
else:
    for doc in documents:
        print(doc)

"""
### RAG를 위한 데이터 인덱스 생성 코드 ###
# 임베딩 모델 로드
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# 문서 임베딩
contents = [doc["content"] for doc in documents]
embeddings = model.encode(contents)

# 임베딩 확인
print(f"Embeddings shape: {embeddings.shape}")

# FAISS 인덱스 생성
dimension = embeddings.shape[1]  # embedding 차원 확인
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

# 검색
query = "간장 보관 방법"  # 여기에서 쿼리를 입력
query_embedding = model.encode([query])
distances, indices = index.search(query_embedding, k=3)

# 검색 결과 출력
for idx in indices[0]:
    print(documents[idx])



### OPENAI에 데이터 제공 ###
def generate_answer(query):
    query_embedding = model.encode([query])
    distances, indices = index.search(query_embedding, k=3)
    
    context = "\n".join([documents[idx]["content"] for idx in indices[0]])
    prompt = (
        f"다음은 관련된 정보입니다:\n{context}\n\n"
        f"질문: {query}\n"
        f"답변:"
    )
    
    response = ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 질문 예제
answer = generate_answer("간장을 개봉 후 어떻게 보관해야 하나요?")
print(answer)
"""