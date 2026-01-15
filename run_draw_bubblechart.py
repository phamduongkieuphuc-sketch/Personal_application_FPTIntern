import requests
import webbrowser
import plotly.express as plx


URL = "http://127.0.0.1:8000/bubble-chart/interactive"
HEADERS = {
    "Content-Type": "application/json"
}

def send_chart_request(data):
    payload = {
        "data": data
    }

    response = requests.post(
        url=URL,
        headers=HEADERS,
        json=payload,
        timeout=30
    )
    
    chart_url = response.json()["chart_url"]
    webbrowser.open(chart_url)
        

if __name__ == "__main__":
    data = [
    {"city": "Hà Nội", "lat": 21.0285, "long": 105.8542, "population": 8400000},

    {"city": "Tokyo", "lat": 35.6895, "long": 139.6917, "population": 13960000},
    {"city": "Shanghai", "lat": 31.2304, "long": 121.4737, "population": 24870000},
    {"city": "Mumbai", "lat": 19.0760, "long": 72.8777, "population": 12480000},
    {"city": "Delhi", "lat": 28.6139, "long": 77.2090, "population": 16790000},
    {"city": "London", "lat": 51.5074, "long": -0.1278, "population": 8900000},
    {"city": "Paris", "lat": 48.8566, "long": 2.3522, "population": 2160000},
    {"city": "New York", "lat": 40.7128, "long": -74.0060, "population": 8300000},
    {"city": "Los Angeles", "lat": 34.0522, "long": -118.2437, "population": 3900000},
    {"city": "São Paulo", "lat": -23.5505, "long": -46.6333, "population": 12300000},
    {"city": "Mexico City", "lat": 19.4326, "long": -99.1332, "population": 9200000},
    {"city": "Cairo", "lat": 30.0444, "long": 31.2357, "population": 10200000},
    {"city": "Lagos", "lat": 6.5244, "long": 3.3792, "population": 15000000},
    {"city": "Istanbul", "lat": 41.0082, "long": 28.9784, "population": 15400000},
    {"city": "Sydney", "lat": -33.8688, "long": 151.2093, "population": 5300000}
    ]

    send_chart_request(data)
    

     
    

