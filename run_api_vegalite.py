import requests
import json

with open("chart.json") as f:
    spec = json.load(f)

r = requests.post("http://127.0.0.1:8000/render", json=spec)
r.raise_for_status()

with open("chart.png", "wb") as f:
    f.write(r.content)
