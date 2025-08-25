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
                cur.execute(sql_product_id, (review['상품ID'],))
                product = cur.fetchone()
                if not product:
                    continue
                goodsID = product[0]
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
    finally:
        conn.close()



# 분석테이블 전처리 된 상품목록 DB 저장
def insert_product_list():
    conn = dbcon()
    try:
        with conn.cursor() as cur:
            # tb_products에서 모든 상품 가져오기
            cur.execute("SELECT ID, product_name FROM tb_products")
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
    inserted_reviews = []

    with conn.cursor() as cur:
        # 리뷰 + productID 같이 가져오기
        cur.execute("SELECT r.reviewID, r.comment, p.productID "
                    "FROM tb_reviews r "
                    "JOIN tb_products p ON r.goodsID = p.ID")
        result = cur.fetchall()
        for review_id, review_text, productID in result:
            if review_text in exclude_texts:
                continue
            inserted_reviews.append((review_id, review_text, productID))
    conn.close()
    print(f"제거완료, 분석할 리뷰 수 {len(inserted_reviews)}개")
    return inserted_reviews




# 분석테이블에 LLM (리뷰 카테고리, 키워드 ,감성) 분석 내용 DB 저장 + 키워드 저장 
def save_analyze_review(all_results):
    conn = dbcon()
    try:
        with conn.cursor() as cur:
            
            # 키워드 +1 카운트해서 DB저장 있으면 +1, 없으면 insert 
            def insert_keyword(cur, productID, categoryID, keywords):
                if not keywords:
                    # print(f"[DEBUG] 키워드 없음 → productID={productID}")
                    return
                
                for kw in keywords:
                    # 1. 이미 있는 키워드 확인
                    cur.execute("""
                        SELECT keyword_id, count FROM tb_keywords
                        WHERE productID=%s AND categoryID=%s AND keyword=%s
                    """, (productID, categoryID, kw))
                    data = cur.fetchone()

                    # 2. 없으면 INSERT
                    if data is None:
                        cur.execute("""
                            INSERT INTO tb_keywords (productID, categoryID, keyword, count)
                            VALUES (%s, %s, %s, 1)
                        """, (productID, categoryID, kw))
                        # print(f"[DEBUG] 키워드 신규 저장 → productID={productID} keyword={kw}")
                    # 3. 있으면 count + 1
                    else:
                        cur.execute("UPDATE tb_keywords SET count=count+1 WHERE keyword_id=%s", (data[0],))
                        # print(f"[DEBUG] 키워드 count +1 → productID={productID} keyword={kw} old_count={data[1]}")

            for item in tqdm(all_results, desc="분석 결과 DB 저장 및 키워드 처리"):
                productID = item["productID"]
                cur.execute("SELECT categoryID FROM tb_categories WHERE category=%s", (item['category'],))
                cat = cur.fetchone()
                if not cat:
                    # print(f"[DEBUG] category 미존재 → {item['category']}")
                    continue
                categoryID = cat[0]

                cur.execute("SELECT sentiment FROM tb_analyze WHERE reviewID=%s AND productID=%s",
                            (item["review_id"], productID))
                if cur.fetchone():
                    # print(f"[DEBUG] 이미 분석된 리뷰 건너뜀 → reviewID={item['review_id']}")
                    continue

                cur.execute("INSERT INTO tb_analyze (productID, reviewID, sentence, sentiment) VALUES (%s,%s,%s,%s)",
                            (productID, item["review_id"], item["sentence"], item["sentiment"]))
                # print(f"[DEBUG] tb_analyze 저장 완료 → reviewID={item['review_id']}")

                # 키워드 저장
                insert_keyword(cur, productID, categoryID, item["keywords"])
                # print(f"[DEBUG] insert_keyword 저장 완료 → reviewID={item['review_id']} keywords={item['keywords']}")

        conn.commit()
        print(f"분석DB 및 키워드 DB 저장 완료! 총 {len(all_results)}개 처리")
    finally:
        conn.close()