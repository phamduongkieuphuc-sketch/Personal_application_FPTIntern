import requests
import json
import webbrowser

BASE_URL = "http://127.0.0.1:8000"
CHART_URL = f"{BASE_URL}/chart"

HEADERS = {
    "Content-Type": "application/json"
}

def send_chart_request(data, question):
    payload = {
        "data": data,
        "question": question,
    }

    response = requests.post(
        url=CHART_URL,
        headers=HEADERS,
        json=payload,
        timeout=60
    )

    response.raise_for_status()
    return response.json()


def absolutize_urls(result: dict) -> dict:
    for key in ("view_url", "image_url", "spec_url"):
        if key in result and result[key]:
            result[key] = BASE_URL + result[key]
    return result


if __name__ == "__main__":

    with open("test/test_6.txt", "r") as f:
        file_content = f.read().strip()
        print(file_content)
        
    json_str = f"[{file_content}]"
    data = json.loads(json_str)

    print(data)

    question = "Create the most suitable chart to represent the data"
    result = send_chart_request(data, question)
    result = absolutize_urls(result)

    print(json.dumps(result, indent=2, ensure_ascii=False))

    # auto-open chart in browser
    if "view_url" in result:
        webbrowser.open(result["view_url"])


