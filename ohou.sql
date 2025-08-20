truncate table tb_products;
truncate table tb_reviews;

DROP DATABASE ai_reviews;

create database ai_reviews CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

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


SELECT *
FROM tb_reviews
WHERE goodsID = 1
ORDER BY event_date DESC, reviewID DESC;



-- 분석 
CREATE TABLE tb_analyzer (

  productID INT,
  clean_name VARCHAR(255),
  reviewID INT NOT NULL UNIQUE,
  comment LONGTEXT,
  grade FLOAT,
  keywords VARCHAR(255)
  
);

CREATE TABLE tb_category (

  category ENUM("배송","사용감","사이즈","디자인","품질"),

);