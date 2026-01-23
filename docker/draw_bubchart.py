import plotly.express as plx
import pandas as pd
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from fastapi.responses import HTMLResponse, RedirectResponse
from uuid import uuid4
from pathlib import Path

CHART_RECORD = {}

load_dotenv()
FPT_API_KEY = os.getenv("FPT_CLOUD_API_KEY")
API_URL = "https://mkp-api.fptcloud.com/v1/chat/completions"
MODEL_NAME = "Qwen2.5-Coder-32B-Instruct"


headers = {
    "Authorization": f"Bearer {FPT_API_KEY}",
    "Content-Type": "application/json",
    }

class Data(BaseModel):
    city: str
    lat: float
    long: float
    population: float

class BubbleChart(BaseModel):
    data: List[Data]

app = FastAPI()
def create_bubble_chart(data):
    print("REACHED HERE @2")
    df = pd.DataFrame(data)

    print("REACHED HERE @3")

    fig = plx.scatter_geo(
        df,
        lat="lat",
        lon="long",
        size="population",
        hover_name="city",
        size_max=45,
        projection="natural earth",
        title="Population bubble chart",
        )
    
    print("REACHED HERE @4")

    min_lat = min(item["lat"] for item in data)
    max_lat = max(item["lat"] for item in data)
    min_long = min(item["long"] for item in data)
    max_long = max(item["long"] for item in data)

    print("REACHED HERE @5")


    fig.update_layout(
        geo=dict(
            showcountries=True,
            countrycolor="lightgray",
            lataxis_range=[min_lat - 5, max_lat + 5],
            lonaxis_range=[min_long - 5, max_long + 5],
            showcoastlines=True,
            coastlinecolor="gray",
            )
    )

    print("REACHED HERE @6")

    
    return fig

@app.post("/bubble-chart/interactive")
def bubble_chart_interactive(request: BubbleChart):
    fig = create_bubble_chart(request.data)

    # Ensure output directory exists
    output_dir = Path("population bubble charts")
    output_dir.mkdir(exist_ok=True)

    file_id = uuid4()
    image_path = output_dir / f"bubble_chart_{file_id}.png"

    # Save image
    fig.write_image(
        image_path,
        width=1200,
        height=700,
        scale=2
    )

    chart_html = fig.to_html(
        full_html=True,
        include_plotlyjs="cdn"
    )

    chart_id = str(uuid4())
    CHART_RECORD[chart_id] = chart_html

    return {
        "chart_url": f"http://127.0.0.1:8000/bubble-chart/view/{chart_id}"
    }


@app.get("/bubble-chart/view/{chart_id}", response_class=HTMLResponse)
def view_chart(chart_id: str):
    html = CHART_RECORD.get(chart_id)
    if not html:
        return HTMLResponse("Chart not found", status_code=404)

    return html



