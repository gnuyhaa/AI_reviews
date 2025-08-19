from DB.db import insert_product, insert_product_review
from crawler import product_list, product_review


insert_product(product_list())

insert_product_review(product_review(pages=3))
