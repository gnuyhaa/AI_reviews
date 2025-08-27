USE ai_reviews;


CREATE TABLE tb_products (
    ID INT NOT NULL AUTO_INCREMENT,
    productID INT,
    brand_name VARCHAR(255),
    product_name VARCHAR(255),

    PRIMARY KEY (ID)
);

CREATE TABLE tb_reviews (
    ID INT NOT NULL AUTO_INCREMENT,
		goodsID INT NOT NULL,
		reviewID INT NOT NULL UNIQUE,
    customerID INT,
    nickname VARCHAR(255),
		options VARCHAR(255),
    grade FLOAT,
    comment LONGTEXT,
    event_date DATE,

    PRIMARY KEY (ID),
		FOREIGN KEY (goodsID) REFERENCES tb_products(ID)
);

-- 분석

CREATE TABLE tb_analyze (
    analyzeID INT AUTO_INCREMENT PRIMARY KEY,
    productID INT NOT NULL,
    reviewID INT NOT NULL,
    sentence LONGTEXT,
    sentiment VARCHAR(255),
    FOREIGN KEY (productID) REFERENCES tb_products(ID)
);

-- 상품 전처리 테이블 만들기 ...
CREATE TABLE tb_analyze_products (
  productID INT PRIMARY KEY,
  clean_name VARCHAR(255),

	FOREIGN KEY (productID) REFERENCES tb_products(ID)
);

-- 카테고리 테이블 만들기 
CREATE TABLE tb_categories (
  categoryID INT AUTO_INCREMENT PRIMARY KEY,
  category VARCHAR(255)
);

insert into tb_categories (category) values ('배송');
insert into tb_categories (category) values ('사용감');
insert into tb_categories (category) values ('사이즈');
insert into tb_categories (category) values ('디자인');
insert into tb_categories (category) values ('품질');


-- 키워드 테이블 .. 만들기 
CREATE TABLE tb_keywords (
  keyword_id INT AUTO_INCREMENT PRIMARY KEY,
  productID INT NOT NULL,
  categoryID INT NOT NULL,
  keyword VARCHAR(50) NOT NULL,
  count INT NOT NULL DEFAULT 1,

	FOREIGN KEY (productID) REFERENCES tb_analyze_products(productID),
	FOREIGN KEY (categoryID) REFERENCES tb_categories(categoryID)
);

