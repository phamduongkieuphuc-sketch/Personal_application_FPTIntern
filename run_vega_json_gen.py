import requests
import json

URL = "http://127.0.0.1:8000/chart"
HEADERS = {
    "Content-Type": "application/json"
}

def send_chart_request(data, question):
    payload = {
        "data": data,
        "question": question,
    }

    response = requests.post(
        url=URL,
        headers=HEADERS,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    return response.json()

if __name__ == "__main__":
    data = [
        {"product_name": "thit lon", "revenue": 10000000}, {"product_name": "thit bo", "revenue": 7600000}, {"product_name": "thit ga", "revenue": 2000000},
      {"product_name": "thit cuu", "revenue": 3000000}, {"product_name": "thit kangaroo", "revenue": 1000000},
    ]
    question = "Top 3 san pham co doanh thu cao nhat"

    question_1 = "Ty le doanh thu cac san pham trong thang truoc bang bieu do tron"


    result = send_chart_request(data, question_1)

    result["view_url"] = f"http://127.0.0.1:8000{result['view_url']}"
    result["image_url"] = f"http://127.0.0.1:8000{result['image_url']}"
    result["spec_url"] = f"http://127.0.0.1:8000{result['spec_url']}"

    print(json.dumps(result, indent=2))

