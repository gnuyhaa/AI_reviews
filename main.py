from DB.db import insert_product, insert_product_review
from crawler import product_list, product_review


insert_product(product_list())  # 상품목록 크롤링 + DB 저장

insert_product_review(product_review(pages=5))  # 리뷰 크롤링 + DB 저장
