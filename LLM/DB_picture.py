from dotenv import load_dotenv
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time


# 환경 변수 로드
load_dotenv()

def search_images(query):
    encoded_query = urllib.parse.quote(query)
    url = f'https://search.naver.com/search.naver?sm=tab_hty.top&where=image&ssc=tab.image.all&query={encoded_query}+" 제품"'

    # 셀레니움 설정
    options = Options()
    options.add_argument("--headless")  # 브라우저를 띄우지 않고 실행
    options.add_argument("--no-sandbox")

    # 크롬 드라이버 경로 설정
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)

    # 페이지 로딩을 기다리기 (동적 페이지를 위해 잠시 대기)
    time.sleep(3)

    # 이미지 소스를 추출
    image_urls = []
    try:
        # 수정된 CSS 선택자로 이미지 추출
        images = driver.find_elements(By.CSS_SELECTOR, "#main_pack > section.sc_new.sp_nimage._fe_image_viewer_prepend_target._fe_image_tab_content_root > div.api_subject_bx._fe_image_tab_grid_root.ani_fadein > div > div > div.image_tile._fe_image_tab_grid > div:nth-child(1) > div > div > div > img")
        for img in images:
            img_url = img.get_attribute("src")
            if img_url:
                image_urls.append(img_url)

        if image_urls:
            return image_urls[0]
    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        driver.quit()

# 메인 함수
if __name__ == "__main__":
    # 이미지 정보 반환
    image_urls = search_images("서울우유")
    print(image_urls)

