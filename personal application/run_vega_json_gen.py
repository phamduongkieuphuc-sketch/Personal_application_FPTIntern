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
      {"category":"A", "group": "x", "value":0.1},
      {"category":"A", "group": "y", "value":0.6},
      {"category":"A", "group": "z", "value":0.9},
      {"category":"B", "group": "x", "value":0.7},
      {"category":"B", "group": "y", "value":0.2},
      {"category":"B", "group": "z", "value":1.1},
      {"category":"C", "group": "x", "value":0.6},
      {"category":"C", "group": "y", "value":0.1},
      {"category":"C", "group": "z", "value":0.2}
    ]

    print(data)

    question_1 = "Tao bieu do phu hop cho so lieu"


    result = send_chart_request(data, question_1)

    result["view_url"] = f"http://127.0.0.1:8000{result['view_url']}"
    result["image_url"] = f"http://127.0.0.1:8000{result['image_url']}"
    result["spec_url"] = f"http://127.0.0.1:8000{result['spec_url']}"

    print(json.dumps(result, indent=2))

