from DB.db import insert_product, insert_product_review, insert_product_list, save_analyze_review
from crawler.crawler import product_list, product_review
from analyzer.ohou_LLM import clean_reviews, analyze_reviews

# 1. 상품 목록 크롤링 + DB 저장
insert_product(product_list())

# 2. 리뷰 크롤링 + DB 저장
insert_product_review(product_review(pages=50)) 

# 3. 상품목록 전처리 DB 저장
insert_product_list()

# 4. 리뷰 전처리
inserted_reviews = clean_reviews()

# 5. LLM 분석
all_results = analyze_reviews(inserted_reviews)

# 6. 분석 결과 DB 저장 (reviewID 포함)
save_analyze_review(all_results)

print("전체 파이프라인 완료!")
