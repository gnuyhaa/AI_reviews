from DB.db import get_latest_review_id
from bs4 import BeautifulSoup
import requests


# 상품 목록 크롤링
def product_list():
    response = requests.get(
        "https://store.ohou.se/ranks?type=best&category_id=18000000",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        },
    )
    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one("head > script:nth-child(31)")
    token = title["src"].split("/")[6]

    url = f"https://store.ohou.se/_next/data/{token}/ko-KR/ranks.json?type=best&category_id=18000000"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    # 요청 보내기
    res = requests.get(url, headers=headers)
    print("응답 상태 코드:", res.status_code)  # 상태 코드 확인

    # JSON 파싱 안전하게
    try:
        data = res.json()
        goods_lists = data["pageProps"]["dehydratedState"]["queries"][1]["state"][
            "data"
        ]["products"]
    except (ValueError, KeyError):
        return []

    # 결과 저장
    result = []
    for goods in goods_lists:
        result.append(
            {
                "상품ID": goods["id"],
                "브랜드명": goods["brandName"],
                "제품명": goods["name"],
            }
        )

    return result[:4]  # 상품4개 가져오기


# 상품 리뷰 크롤링
def product_review(pages=10):
    products = product_list()
    latest_id = get_latest_review_id()
    existing_ids = {latest_id}

    all_reviews = []

    for prod in products:
        product_id = prod["상품ID"]

        # 여러 페이지 리뷰 수집
        for page in range(1, pages + 1):  # 1페이지부터
            url = f"https://ohou.se/production_reviews.json?production_id={product_id}&page={page}&order=recent&photo_review_only="
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            }
            res = requests.get(url, headers=headers)
            try:
                data = res.json()
            except ValueError:
                continue

            if "reviews" not in data:
                continue

            stop_crawling = False
            for r in data["reviews"]:
                review_id = r["id"]
                if review_id in existing_ids:
                    stop_crawling = True
                    break

                all_reviews.append(
                    {
                        "리뷰ID": review_id,
                        "상품ID": r["production_information"]["id"],
                        "고객ID": r["writer_id"],
                        "고객닉네임": r["writer_nickname"],
                        "상품옵션": r["production_information"]["explain"],
                        "별점": r["review"]["star_avg"],
                        "작성내용": r["review"]["comment"],
                        "작성날짜": r["created_at"],
                    }
                )

            if stop_crawling:
                break  # 더 이전 페이지 리뷰 수집 중단

    return all_reviews
