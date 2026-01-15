import os
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from vega_json_gen import generate_vegalite_json, attach_data, validate_vegalite, generate_image_bytes
from draw_bubchart import create_bubble_chart
from typing import Optional, Any, Literal, List, Dict
import json
from uuid import uuid4
from pathlib import Path
from fastapi.responses import HTMLResponse, FileResponse


load_dotenv()
FPT_API_KEY = os.getenv("FPT_CLOUD_API_KEY")
MODEL_NAME = "Qwen2.5-Coder-32B-Instruct"

BASE_DIR = Path("charts")
BASE_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Chart Generator")

class ChartDecison(BaseModel):
    function: Literal["vegalite", "plotly"]
    reason: Optional[str]

llm = ChatOpenAI(
    model=MODEL_NAME,
    api_key=FPT_API_KEY,
    base_url="https://mkp-api.fptcloud.com/v1",
    temperature=1.0,
    max_tokens=1024
)

decision_llm = llm.with_structured_output(ChartDecison)
DECISION_PROMPT = PromptTemplate(
    template="""

You are a chart decision-making assistant.

Rules:
- If the data contains latitude/longitude AND population, then you use plotly to draw population bubble chart
- If the user asks for a map, geographic, globe, world -> use plotly
- Otherwise, use vegalite to represent data in an analytic chart
- Output JSON only

User Question:
{question}

Data:
{data}

""",

input_variables=["question", "data"],
)

class UserRequest(BaseModel):
    question: str
    data: List[Dict[str, Any]]

@app.post("/chart")
def generate_chart(request: UserRequest):
    chart_id = str(uuid4())
    chart_dir = BASE_DIR / chart_id
    chart_dir.mkdir()

    decision = decision_llm.invoke(
        DECISION_PROMPT.format(
            question=request.question,
            data=json.dumps(request.data[:3], ensure_ascii=False) # Get the first 3 samples to decide
        )
    )

    print(decision)

    meta_data = {
        "id": chart_id,
        "function": decision.function,
        "question": request.question,
        "reason": decision.reason,
    }

    if decision.function == "vegalite":
        spec = generate_vegalite_json(request.data, request.question)
        spec = attach_data(spec, request.data)

        try:
            validate_vegalite(spec)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Vegalite Error: {str(e)}")

        image_bytes = generate_image_bytes(spec)

        (chart_dir / "chart.png").write_bytes(image_bytes)
        (chart_dir / "spec.json").write_text(
            json.dumps(spec, indent=2, ensure_ascii=False)
        )

    elif decision.function == "plotly":

        print("REACHED HEERE")
        print(request.data)

        try:
            fig = create_bubble_chart(request.data)
        except Exception as e:
            raise HTTPException(status_code=510, detail=f"Plotly Error: {str(e)}")

        html = fig.to_html(
            full_html=True,
            include_plotlyjs="cdn",
        )

        fig.write_image(
            chart_dir / "chart.png",
            width=1200,
            height=700,
            scale=2,
        )

        (chart_dir / "chart.html").write_text(html, encoding="utf-8")    
    
    else:
        raise HTTPException(status_code=512, detail="Invalid decision made.")
    
    (chart_dir / "meta.json").write_text(
        json.dumps(meta_data, indent=2, ensure_ascii=False)
    )

    return {
        "id": chart_id,
        "function": decision.function,
        "view_url": f"/view/{chart_id}",
        "image_url": f"/image/{chart_id}",
        "spec_url": f"/spec/{chart_id}",
    }

@app.get('/view/{chart_id}', response_class=HTMLResponse)
def view_chart(chart_id: str):
    chart_dir = BASE_DIR / chart_id

    if not chart_dir.exists():
        raise HTTPException(status_code=404, detail="Chart not found")

    meta_data = json.loads((chart_dir / "meta.json").read_text())

    if meta_data["function"] == "plotly":
        return HTMLResponse((chart_dir / "chart.html").read_text())

    # Vega-Lite image view
    html = f"""
    <html>
      <body>
        <h2>Chart {chart_id}</h2>
        <p><strong>Question:</strong> {meta_data["question"]}</p>
        <img src="/image/{chart_id}" style="max-width:800px;" />
        <h3>Vega-Lite Spec</h3>
        <pre>{(chart_dir / "spec.json").read_text()}</pre>
      </body>
    </html>
    """
    return HTMLResponse(html)

@app.get("/image/{chart_id}")
def get_image(chart_id: str):
    path = BASE_DIR / chart_id / "chart.png"
    if not path.exists():
        raise HTTPException(status_code=512, detail="Image not found")
    return FileResponse(path, media_type="image/png")


# ---------------- spec ----------------
@app.get("/spec/{chart_id}")
def get_spec(chart_id: str):
    path = BASE_DIR / chart_id / "spec.json"
    if not path.exists():
        raise HTTPException(status_code=600, detail="Spec not available")
    return json.loads(path.read_text())