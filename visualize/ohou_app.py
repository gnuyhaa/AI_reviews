import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import re
import pandas as pd
import matplotlib.pyplot as plt
from db.db import dbcon

plt.rcParams['font.family'] = 'NanumGothic' 
dbcon()


st.set_page_config('오늘의 집 리뷰 분석','🏠',layout="wide")

# 상품 목록 불러오기 함수
def get_products():
    conn = dbcon()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT productID, clean_name FROM tb_analyze_products")
            rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=["productID", "productName"])
        return df
    finally:
        conn.close()


# 선택된 상품의 리뷰 불러오기 함수
def get_reviews(product_id):
    conn = dbcon()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT r.reviewID, r.nickname, r.grade, r.comment, r.event_date
                FROM tb_reviews r
                JOIN tb_products p ON r.goodsID = p.ID
                JOIN tb_analyze_products ap ON ap.productID = p.ID
                WHERE ap.productID = %s
            """, (product_id,))
            rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=["reviewID", "nickname", "grade", "comment", "event_date"])
        return df
    finally:
        conn.close()


# 선택된 상품이 있으면 평점과 리뷰 수 계산
def get_rating_and_count(product_id):
    conn = dbcon()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT AVG(grade), COUNT(*) FROM tb_reviews WHERE goodsID=%s",
                (product_id,)
            )
            result = cur.fetchone()
            if result:
                avg_grade = float(result[0]) if result[0] is not None else 0
                review_count = int(result[1])
                return avg_grade, review_count
            else:
                return 0, 0
    finally:
        conn.close()

# 선택한 상품의 리뷰 키워드 카운드 
def get_keyword_count(product_id):
    conn=dbcon()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT keyword, sum(count) as co FROM tb_keywords WHERE productID=%s GROUP BY keyword ORDER BY co DESC LIMIT 10", (product_id,))
            rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=["keyword", "count"])
        return df
    finally:
        conn.close()

# 카테고리 가져오기
def get_categories():
    conn = dbcon()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT categoryID, category FROM tb_categories ORDER BY categoryID")
            rows = cur.fetchall()
            return rows 
    finally:
        conn.close()

# 긍정 부정 카운트 
def get_sentiment_count(product_id, category_id):
    conn = dbcon()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.sentiment, COUNT(DISTINCT a.reviewID) AS cnt
                FROM tb_analyze a
                JOIN tb_keywords k
                  ON k.productID = a.productID
                 AND k.categoryID = %s
                WHERE a.productID = %s
                  AND a.sentence LIKE CONCAT('%%', k.keyword, '%%')
                GROUP BY a.sentiment
            """, (category_id, product_id))  # ← 순서 주의: (category_id, product_id)
            rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=["sentiment", "count"])
        return df
    finally:
        conn.close()

# 키워드 카테고리 
def get_keyword_count_by_category(product_id, category_id):
    conn = dbcon()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT keyword, SUM(count) as cnt
                FROM tb_keywords
                WHERE productID=%s AND categoryID=%s
                GROUP BY keyword
                ORDER BY cnt DESC
                LIMIT 3
            """, (product_id, category_id))
            rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=["keyword", "count"])
        return df
    finally:
        conn.close()

# 리뷰 가져오기 
def get_reviews_by_category(product_id, category_id, limit=5):
    conn = dbcon()
    try:
        with conn.cursor() as cur:
            # 리뷰 + 키워드 같이 가져오기
            cur.execute("""
                SELECT 
                    r.reviewID, r.nickname, r.grade, r.comment, r.event_date,
                    GROUP_CONCAT(DISTINCT k.keyword) AS keywords
                FROM tb_reviews r
                JOIN tb_analyze a 
                  ON a.productID = r.goodsID
                 AND a.reviewID  = r.reviewID
                JOIN tb_keywords k
                  ON k.productID = a.productID
                 AND k.categoryID = %s
                WHERE a.productID = %s
                  AND a.sentence LIKE CONCAT('%%', k.keyword, '%%')
                GROUP BY r.reviewID, r.nickname, r.grade, r.comment, r.event_date
                ORDER BY r.event_date DESC
                LIMIT %s
            """, (category_id, product_id, limit))
            rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=["reviewID", "nickname", "grade", "comment", "event_date", "keywords"])
        return df
    finally:
        conn.close()


# 카테고리에 해당하는 키워드 가져오기 
def get_keywords_by_sentiment(product_id, category_id):
    conn = dbcon()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT k.keyword, a.sentiment, COUNT(*) AS hits
                FROM tb_analyze a
                JOIN tb_keywords k
                  ON k.productID = a.productID
                 AND k.categoryID = %s
                WHERE a.productID = %s
                  AND a.sentence LIKE CONCAT('%%', k.keyword, '%%')
                GROUP BY k.keyword, a.sentiment
                ORDER BY hits DESC
            """, (category_id, product_id))
            rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=["keyword", "sentiment", "hits"])
        return df
    finally:
        conn.close()


# 리뷰 하이라이팅 함수
def highlight_multiple_substrings(text, substrings, colors):
    import html
    import re
    
    # 더 세밀한 단위로 분리: 마침표, 느낌표, 물음표, 쉼표, 줄바꿈 기준
    parts = re.split(r'([.!?,\n])', text)
    
    # 분리된 부분을 다시 합치면서 원래 형태 유지
    full_parts = []
    for i in range(0, len(parts), 2):
        if i + 1 < len(parts):
            full_parts.append(parts[i] + parts[i + 1])
        else:
            full_parts.append(parts[i])
    
    result = ""
    
    for part in full_parts:
        # 빈 문자열이나 공백만 있는 경우 건너뛰기
        if not part.strip():
            result += html.escape(part).replace('\n', '<br>')
            continue
            
        part_colored = False
        color_to_use = None
        
        # 각 키워드가 해당 부분에 포함되어 있는지 확인
        for substr, color in zip(substrings, colors):
            if substr in part:
                part_colored = True
                color_to_use = color
                break
        
        if part_colored and color_to_use:
            # 해당 부분에서 \n을 <br>로 변경하여 줄바꿈 유지
            part_html = html.escape(part).replace('\n', '<br>')
            result += f"<span style='background-color:{color_to_use}; color:#000; padding:1px 2px; border-radius:2px;'>{part_html}</span>"
        else:
            # 색칠하지 않을 부분도 \n을 <br>로 변경
            part_html = html.escape(part).replace('\n', '<br>')
            result += part_html
    
    return result
# ---------------------------------------------------------------------------------------
# Streamlit UI - 사이드바

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {
        width: 200px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.image("https://img.hankyung.com/photo/202005/01.22651863.1.jpg")
    
    products = get_products()
    
    if products.empty:
        st.warning("DB에 상품이 없습니다.")
        option = None
    else:
        # selectbox에서 상품명 리스트 사용
        option = st.selectbox("상품 선택", products["productName"].tolist())

st.markdown(f"<h3 style='text-align: center; margin-top: -50px;'>🛍️: {option}</h3>",
    unsafe_allow_html=True)

# 선택된 상품이 있으면 리뷰 가져오기
if option:
    # 선택된 상품의 productID 가져오기
    product_id = products.loc[products["productName"] == option, "productID"].iloc[0]
    
    reviews = get_reviews(product_id)
    

col1, col2, col3 = st.columns([0.8, 3, 1.5])

# 리뷰 평점, 리뷰 수 
with col1:
    if option:
        rating, review_count = get_rating_and_count(product_id)
        max_rating = 5
        percent = rating / max_rating * 100  if max_rating else 0# 채울 비율 %
    else:
        rating, review_count, percent, max_rating = 0, 0, 0, 5
    st.markdown(
    "<h4 style='text-align: center; margin-top: 20px;'>요약</h4>",
    unsafe_allow_html=True
)
    st.markdown(
    "<p style='text-align: center; font-weight: bold;'>사용자 총 평점</p>",
    unsafe_allow_html=True
)
    star_html = f"""
    <div style="display:flex; flex-direction:column; align-items:center; font-size:30px; line-height:1;">
    <div style="position:relative; display:inline-block;">
        <!-- 빨간 별 -->
        <div style="position:absolute; width:{percent}%; overflow:hidden; white-space:nowrap; color:red;">
        ★★★★★
        </div>
        <!-- 회색 별 -->
        <div style="color:lightgray;">
        ★★★★★
        </div>
            </div>
            <div style="font-size:24px; font-weight:bold; margin-top:8px; text-align:center;">
                {rating:.2f}/{max_rating}
            </div>
        </div>
    """
    st.markdown(star_html, unsafe_allow_html=True)
    
    st.markdown("", unsafe_allow_html=True)

    count_html = f"""
    <div style="text-align:center; font-size:16px;">
        <p style='font-weight: bold;'>전체 리뷰수</p>
        <p style="font-size:50px; margin:0;">💬</p>
        <p style="font-size:30px; font-weight:bold; margin-top:4px;">{review_count}</p>
    </div>
    """ 
    st.markdown(count_html, unsafe_allow_html=True)
    

# 리뷰 AI 분석 
categories = get_categories()

with col2:
    st.markdown("<h4 style='text-align: center; margin-top: 20px;'>리뷰 AI 분석</h4>", unsafe_allow_html=True)

# ------------------- 카테고리 UI 버튼 -------------------
    if "selected_categories" not in st.session_state:
        st.session_state["selected_categories"] = [] 

    # 1) 카테고리 버튼 (선택/해제)
    if categories:
        cols = st.columns(len(categories), gap="small") 
        for i, (cat_id, cat_name) in enumerate(categories):
            if cols[i].button(cat_name, key=f"cat_{cat_id}"):
                if (cat_id, cat_name) in st.session_state["selected_categories"]:
                    st.session_state["selected_categories"].remove((cat_id, cat_name))
                else:
                    st.session_state["selected_categories"].append((cat_id, cat_name))
                    if len(st.session_state["selected_categories"]) > 3:
                        st.session_state["selected_categories"].pop(0)  # 3개 초과시 오래된거 제거

    # 2) 선택된 카테고리 이름만 출력
    bar_cols = st.columns(3, gap="small")
    for i, col in enumerate(bar_cols):
        with col:
            if i < len(st.session_state["selected_categories"]):
                _, cat_name = st.session_state["selected_categories"][i]
                st.markdown(
                    f"<div style='text-align:center; font-weight:bold; font-size:18px; color:#2c3e50;'>{cat_name}</div>",
                    unsafe_allow_html=True
                )

    # 3) 카테고리별 분석 결과 (최대 3개)
    bar1, bar2, bar3 = st.columns(3)
    bar_containers = [bar1, bar2, bar3]

    for i, (category_id, cat_name) in enumerate(st.session_state["selected_categories"][:3]):
        with bar_containers[i]:

            # (1) 긍정부정 파이차트
            sentiment_df = get_sentiment_count(product_id, category_id)
            if not sentiment_df.empty:
                fig, ax = plt.subplots()
                colors = ["#49CBF3", "#FF7D73"]
                wedgeprops={'width': 0.55, 'edgecolor': 'w', 'linewidth': 4}
                wedges, _ = ax.pie(
                    sentiment_df["count"],
                    labels=None,
                    startangle=90,
                    colors=colors,
                    wedgeprops=wedgeprops
                )
                ax.legend(
                    wedges,
                    sentiment_df["sentiment"],
                    loc="upper center",
                    bbox_to_anchor=(0.5, -0.1),
                    fontsize=16,
                    ncol=len(sentiment_df)
                )
                st.pyplot(fig)
            else:
                st.info("해당 카테고리 키워드가 포함된 리뷰가 없습니다.")

            # (2) 키워드 상위 3개 바차트
            keyword_df = get_keyword_count_by_category(product_id, category_id).head(3)
            if not keyword_df.empty:
                colors = ["#87C9FF", "#FFE083", "#ED87FF"]
                fig2, ax2 = plt.subplots()
                bars2 = ax2.bar(keyword_df['keyword'], keyword_df['count'], color=colors)
                ax2.set_xticklabels([])
                ax2.legend(
                    bars2,
                    keyword_df["keyword"],
                    loc="upper center",
                    bbox_to_anchor=(0.5, -0.1),
                    fontsize=19,
                    ncol=len(keyword_df)
                )
                st.pyplot(fig2)
            else:
                st.info("키워드 없음")

            # (3) 리뷰 보여주기
            review_df = get_reviews_by_category(product_id, category_id, limit=5)

            if not review_df.empty:
                # 키워드별 긍/부정 정보 불러오기
                keyword_sentiment_df = get_keywords_by_sentiment(product_id, category_id)

                # {keyword: color} 매핑 만들기
                keyword_colors = {}
                for _, row in keyword_sentiment_df.iterrows():
                    if row["sentiment"] == "긍정":
                        keyword_colors[row["keyword"]] = "#96E2F9"   # 연한 파랑
                    else:
                        keyword_colors[row["keyword"]] = "#fdaaaa"   # 연한 빨강

                for _, row in review_df.iterrows():
                    keywords = row["keywords"].split(",") if row["keywords"] else []
                    colors = [keyword_colors.get(k, "#FFEB99") for k in keywords]  # 기본은 노랑

                    highlighted_comment = highlight_multiple_substrings(
                        row["comment"], keywords, colors
                    )

                    review_html = f"""
                    <div style="border:1px solid #ddd; border-radius:8px; padding:10px; margin-bottom:8px;">
                        <p style="margin:0;">{highlighted_comment}</p>
                        <p style="margin:4px 0 0 0; font-size:12px; color:#666;">
                            ({row['event_date'].strftime('%Y-%m-%d')})
                        </p>
                    </div>
                    """
                    st.markdown(review_html, unsafe_allow_html=True)
            else:
                st.info("해당 카테고리에 해당하는 리뷰가 없습니다.")



# 리뷰 키워드 분석
with col3:
    st.markdown(
    "<h4 style='text-align: center; margin-top: 20px;'>리뷰 키워드 분석</h4>",
    unsafe_allow_html=True
    )
    # 선택된 상품이 있으면 키워드 가져오기
    if option:
        # 선택된 상품의 productID 가져오기
        product_id = products.loc[products["productName"] == option, "productID"].iloc[0]
        reviews = get_keyword_count(product_id)

        if reviews.empty:
            st.info("선택한 상품에 대한 키워드가 없습니다.")
        else:
            max_count = reviews["count"].max()
            st.dataframe(
                reviews,
                column_config={
                    "count": st.column_config.ProgressColumn(
                        "count",
                        format="",
                        min_value=0,
                        max_value=int(max_count),  # 최대값보다 여유 있게
                    ),
                },
                hide_index=True
            )