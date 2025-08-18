CREATE TABLE `tb_products` (
	`productID`	INT	NOT NULL,
	`brand_name`	VARCHAR(255)	NULL,
	`product_name`	VARCHAR(255)	NULL,
	`Field`	VARCHAR(255)	NULL
);

-- CREATE TABLE `tb_ai` (
-- 	`category`	VARCHAR(255)	NULL,
-- 	`brand_name`	VARCHAR(255)	NULL,
-- 	`Field3`	VARCHAR(255)	NULL,
-- 	`Field`	VARCHAR(255)	NULL,
-- 	`Field2`	VARCHAR(255)	NULL
-- );

CREATE TABLE `tb_reviews` (
	`productID`	INT	NOT NULL,
	`customerID`	INT	NULL,
	`nickname`	VARCHAR(255)	NULL,
	`grade`	FLOAT	NULL,
	`event_date`	DATE	NULL,
	`comment`	LONGTEXT	NULL
);

ALTER TABLE `tb_products` ADD CONSTRAINT `PK_TB_PRODUCTS` PRIMARY KEY (
	`productID`
);

