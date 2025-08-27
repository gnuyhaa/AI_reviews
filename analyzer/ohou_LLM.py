from db.db import dbcon
import re
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from tqdm import tqdm


## 분석 돌릴 리뷰 전처리
def clean_reviews(exclude_texts=None):
    if exclude_texts is None:
        exclude_texts = [
            "최고예요",
            "마음에 들어요",
            "보통이에요",
            "별로예요",
            "매우 아쉬워요",
        ]

    conn = dbcon()
    inserted_reviews = []

    with conn.cursor() as cur:
        # 리뷰 + 상품명 가져오기
        cur.execute(
            """
            SELECT r.reviewID, r.comment, p.ID
            FROM tb_reviews r
            JOIN tb_products p ON r.goodsID = p.ID
        """
        )
        result = cur.fetchall()

        for review_id, review_text, product_ID in result:
            if review_text in exclude_texts:
                continue
            inserted_reviews.append((review_id, review_text, product_ID))

    print(f"제거완료, 분석할 리뷰 수 {len(inserted_reviews)}개")
    return inserted_reviews


# 리뷰 카테고리, 키워드, 감성 분류
dbcon()
llm = ChatOpenAI(model="gpt-4o-mini")

# 문장별 카테고리 분류
category_prompt = ChatPromptTemplate.from_template(
    """
    You are a classification assistant.
    Classify the given sentence into one of the following categories:

    - 배송: 배송 속도, 포장, 상태와 관련된 내용
    - 사용감: 사용 후 체감, 촉감, 착용감, 사용 경험
    - 사이즈: 크기, 길이, 넓이
    - 디자인: 색상, 모양, 스타일, 미적 요소
    - 품질: 내구성, 마감, 소재, 제품 완성도

    Rules:
    - If no category matches, return "None".
    - Return result in JSON format.
    - Do not include any backslashes (`\`) or escape sequences. 
    - If the input sentence has line breaks, replace them with a single space.

    Input sentence: "{sentence}"
    Output:
    {{
      "sentence": "{sentence}",
      "category": "사용감"
    }}
    """
)
category_chain = category_prompt | llm | JsonOutputParser()

# 키워드 추출
keyword_prompt = ChatPromptTemplate.from_template(
    """
    Extract 1-5 **nouns only** from the following sentence. 
    Exclude general emotion words like "좋아요", "만족", "최고".
    If no obvious product-related noun exists, pick the most meaningful noun in the sentence.
    Return result in **strict JSON format**.
    Do not include any backslashes (`\`) or escape sequences.
    If the input sentence has line breaks, replace them with a single space.

    Sentence: "{sentence}"

    Output:
    {{
      "sentence": "{sentence}",
      "keywords": ["배송"]
    }}
    """
)
keyword_chain = keyword_prompt | llm | JsonOutputParser()

# 감성 분석 프롬프트
sentiment_prompt = ChatPromptTemplate.from_template(
    """
    Determine the sentiment of the given sentence.
    Return "긍정", "부정".
    Return result in strict JSON format.
    Do not include any backslashes (`\`) or escape sequences.
    If the input sentence has line breaks, replace them with a single space.

    Sentence: "{sentence}"

    Output:
    {{
      "sentence": "{sentence}",
      "sentiment": "긍정"
    }}
    """
)
sentiment_chain = sentiment_prompt | llm | JsonOutputParser()


# 실행
def analyze_reviews(inserted_reviews):
    all_results = []

    for rid, rtext, productID in tqdm(inserted_reviews, desc="리뷰 분석 진행"):
        # 리뷰를 문장 단위로 분리
        sentences = re.split(r"(?<=[.!?])[\s\n]+", rtext)
        sentences = [s.strip() for s in sentences if s.strip()]  # 빈문장 제거

        for sent in tqdm(sentences, desc=f"리뷰ID {rid}문장 분석", leave=False):
            if not sent.strip():
                continue

            # 카테고리 분류
            category_result = category_chain.invoke({"sentence": sent})

            if category_result["category"] != "None":  # 카테고리가 있는 문장만
                # 키워드 추출
                kw_result = keyword_chain.invoke({"sentence": sent})

                # 감성 분석
                sentiment_result = sentiment_chain.invoke({"sentence": sent})

                all_results.append(
                    {
                        "productID": productID,
                        "review_id": rid,
                        "sentence": sent,
                        "category": category_result["category"],
                        "keywords": kw_result["keywords"],
                        "sentiment": sentiment_result["sentiment"],
                    }
                )

    print(f"LLM 분석 완료! 총 {len(all_results)}개의 문장이 처리되었습니다.")
    return all_results
