import pymysql
from dotenv import load_dotenv
import os
import re
from tqdm import tqdm

# DB 연결
def dbcon():
    load_dotenv()
    conn = pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_DATABASE'),
        charset="utf8mb4",
    )
    return conn

# DB에서 최신 리뷰 ID 가져오기
def get_latest_review_id():
    conn = dbcon()
    latest_id = 0
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT reviewID FROM tb_reviews ORDER BY reviewID DESC LIMIT 1")
            result = cur.fetchone()
            if result:
                latest_id = result[0]
    finally:
        conn.close()
    return latest_id

# DB에 상품정보 저장 (중복 체크)
def insert_product(products):
    conn = dbcon()
    try:
        with conn.cursor() as cur:
            sql_check = "SELECT ID FROM tb_products WHERE productID=%s"
            sql_insert = "INSERT INTO tb_products (productID, brand_name, product_name) VALUES (%s, %s, %s)"
            
            for data in products:
                cur.execute(sql_check, (data['상품ID'],))
                exists = cur.fetchone()
                if not exists:
                    cur.execute(sql_insert, (data['상품ID'], data['브랜드명'], data['제품명']))
        conn.commit()
    finally:
        conn.close()

# DB에 상품 리뷰 저장 (최신 리뷰 체크 포함)
def insert_product_review(reviews):
    latest_id = get_latest_review_id()
    existing_ids = {latest_id} 
    
    conn = dbcon()
    try:
        with conn.cursor() as cur:
            sql_product_id = "SELECT ID FROM tb_products WHERE productID=%s"
            sql_insert_review = """
                INSERT INTO tb_reviews 
                (goodsID, reviewID, customerID, nickname, options, grade, comment, event_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE reviewID = reviewID 
            """


            for review in reviews:
                if review['리뷰ID'] in existing_ids:
                    print(f"이미 DB에 있는 리뷰 발견. 리뷰ID={review['리뷰ID']} 이후 중단")
                    break

                # 상품 ID 가져오기
                product_id = review['상품ID']
                cur.execute(sql_product_id, (product_id,))
                product = cur.fetchone()
                goodsID = product[0]

                # 리뷰 저장
                cur.execute(sql_insert_review, (
                    goodsID,
                    review['리뷰ID'],
                    review['고객ID'],
                    review['고객닉네임'],
                    review['상품옵션'],
                    float(review['별점']),
                    review['작성내용'],
                    review['작성날짜']
                ))
        conn.commit()
        print("리뷰 저장 완료!")
    finally:
        conn.close()



# 분석테이블 전처리 된 상품목록 DB 저장
def insert_product_list():
    conn = dbcon()
    try:
        with conn.cursor() as cur:
            # tb_products에서 모든 상품 가져오기
            cur.execute("SELECT productID, product_name FROM tb_products")
            result = cur.fetchall()

            for productID, name in result:
                clean_name = re.sub(r"\[.*?\]", "", name)  # 괄호 제거 등 전처리

                # 중복 발생 시 clean_name만 업데이트
                cur.execute(
                    """
                    INSERT INTO tb_analyze_products (productID, clean_name)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE clean_name=VALUES(clean_name)
                    """,
                    (productID, clean_name)
                )

            conn.commit()
            print("분석DB에 전처리 상품목록 저장 완료! (중복 처리 포함)")
    finally:
        conn.close()

# 분석테이블에 전처리된 리뷰내용 DB 저장
def insert_clean_review(exclude_texts=None):
    if exclude_texts is None:
        exclude_texts = ["최고예요", "마음에 들어요", "보통이에요", "별로예요", "매우 아쉬워요"]

    conn = dbcon()
    try:
        with conn.cursor() as cur:
            # 원본 리뷰 불러오기
            cur.execute("SELECT reviewID, comment FROM tb_reviews")
            result = cur.fetchall()

            inserted_reviews = []

            for review_id, review_text in result:
                if review_text in exclude_texts:
                    continue  # 제외

                inserted_reviews.append((review_id, review_text))

                # tb_analyze에 삽입
                cur.execute(
                    "INSERT INTO tb_analyze (reviewID, comment) VALUES (%s, %s)",
                    (review_id, review_text)
                )

            conn.commit()
            print(f"분석DB에 전처리 리뷰 저장 완료! 총 {len(inserted_reviews)}개 삽입")

    finally:
        conn.close()


# 분석테이블에 LLM (리뷰 카테고리, 키워드 ,감성) 분석 내용 DB 저장
def insert_analyze_review(all_results):
    conn = dbcon()
    try:
        with conn.cursor() as cur:
            for item in tqdm(all_results, desc="DB 저장 진행"):
                cur.execute(
                    """
                    INSERT INTO tb_analyze (reviewID, sentence, category, keywords, sentiment)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        category=VALUES(category),
                        keywords=VALUES(keywords),
                        sentiment=VALUES(sentiment)
                    """,
                    (
                        item["review_id"],
                        item["sentence"],
                        item["category"],
                        ",".join(item["keywords"]),
                        item["sentiment"]
                    )
                )
        conn.commit()
        print(f"분석DB에 LLM 분석 결과 저장 완료! 총 {len(all_results)}개 삽입")
    finally:
        conn.close()
