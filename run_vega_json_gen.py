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
        {"province": "Hà Nội", "lat": 21.0285, "lon": 105.8542, "population": 8400000},
                {"province": "TP.HCM", "lat": 10.8231, "lon": 106.6297, "population": 9300000},
                {"province": "Đà Nẵng", "lat": 16.0544, "lon": 108.2022, "population": 1200000},
                {"province": "Hải Phòng", "lat": 20.8449, "lon": 106.6881, "population": 2100000},
                {"province": "Cần Thơ", "lat": 10.0452, "lon": 105.7469, "population": 1250000},
    ]
    question = "Top 3 san pham co doanh thu cao nhat"

    question_1 = "Tao bieu do dan so bubble chart"


    result = send_chart_request(data, question_1)

    result["view_url"] = f"http://127.0.0.1:8000{result['view_url']}"
    result["image_url"] = f"http://127.0.0.1:8000{result['image_url']}"
    result["spec_url"] = f"http://127.0.0.1:8000{result['spec_url']}"

    print(json.dumps(result, indent=2))

