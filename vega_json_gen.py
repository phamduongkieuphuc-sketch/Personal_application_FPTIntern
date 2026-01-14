#----- Using with_structured_output() -------
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import requests
from jsonschema import validate
import vl_convert as vlc
from uuid import uuid4
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Literal
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

load_dotenv()
FPT_API_KEY = os.getenv("FPT_CLOUD_API_KEY")
print(FPT_API_KEY)
API_URL = "https://mkp-api.fptcloud.com/v1/chat/completions"
MODEL_NAME = "Qwen2.5-Coder-32B-Instruct"
VEGALITE_SCHEMA_URL = "https://vega.github.io/schema/vega-lite/v6.json"

headers = {
    "Authorization": f"Bearer {FPT_API_KEY}",
    "Content-Type": "application/json",
    }

class VegaLiteData(BaseModel):
    name: Literal["input_data"] = "input_data"


class VegaLiteSpec(BaseModel):
    vgl_schema: str = Field("https://vega.github.io/schema/vega-lite/v6.json", alias="$schema")
    description: Optional[str]
    data: VegaLiteData
    mark: Any
    encoding: Dict[str, Any]
    transform: Optional[list]

llm = ChatOpenAI(
    model=MODEL_NAME,
    api_key=FPT_API_KEY,
    base_url="https://mkp-api.fptcloud.com/v1",
    temperature=1.0,
    max_tokens=1024
)

structured_llm = llm.with_structured_output(VegaLiteSpec)

SYSTEM_PROMPT = PromptTemplate(
    template="""
You are a data visualization expert.

Your task:
- Generate a valid Vega-Lite v6 JSON specification
- Use named data source: "input_data"
- Choose the most appropriate chart type
- Output JSON ONLY

Data:
{data}

User Question:
{question}
""",
    input_variables=["data", "question"],
)



app = FastAPI(title="VegaLite Data Visualisation")

#------ Request -------
class ChartRequest(BaseModel):
    data: list
    question: str

# ----- LLM call ------
def generate_vegalite_json(data, question):
    user_prompt = SYSTEM_PROMPT.format(
        data=json.dumps(data, ensure_ascii=False),
        question=question
    )

    try:
        spec: VegaLiteSpec = structured_llm.invoke(user_prompt)
    except Exception as e:
        raise HTTPException(status_code=511, detail=f"LLM failed to produce valid VegaLite spec: {str(e)}")
    
    return spec.model_dump(by_alias=True, exclude_none=True)

#------ Attach Named Data -------
def attach_data(spec, data):
    spec["datasets"] = {
        "input_data": data,
    }
    return spec

# ----- Validate that it is VegaLite JSON ------
def validate_vegalite(spec):
    schema = requests.get(VEGALITE_SCHEMA_URL).json()
    validate(instance=spec, schema=schema)

# --- From VegaLite JSON to image ---
def generate_image_bytes(spec):
    png_image_bytes= vlc.vegalite_to_png(json.dumps(spec), scale=2)
    return png_image_bytes

def save_png_file(png_bytes, file_path="chart.png"):
    with open(file_path, "wb") as f:
        f.write(png_bytes)

BASE_DIR = Path("charts")
BASE_DIR.mkdir(exist_ok=True)

@app.post('/chart')
def generate_chart(query: ChartRequest):
    chart_id = str(uuid4())
    chart_dir = BASE_DIR / chart_id
    chart_dir.mkdir()

    spec = generate_vegalite_json(query.data, query.question)
    spec = attach_data(spec, query.data)

    try:
        validate_vegalite(spec)
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Invalid VegaLite spec: {str(e)}")
    
    # Save files
    png_path = chart_dir / "chart.png"
    spec_path = chart_dir / "spec.json"
    meta_path = chart_dir / "meta.json"
    
    png = generate_image_bytes(spec)
    output_path = "chart.png"

    save_png_file(png, output_path)

    png_path.write_bytes(png)
    spec_path.write_text(json.dumps(spec, indent=4))
    meta_path.write_text(json.dumps({
        "id": chart_id,
        "question": query.question,
    }, indent=4))

    return {
        "id": chart_id,
        "view_url": f"/{chart_id}",
        "image_url": f"/image/{chart_id}",
        "spec_url": f"/spec/{chart_id}"
    }

@app.get("/image/{chart_id}")
def get_image(chart_id):
    path = BASE_DIR / chart_id / "chart.png"
    if not path.exists():
        raise HTTPException(status_code=502, detail="Image doesn't exits.")

    return FileResponse(path, media_type="image/png")

@app.get("/spec/{chart_id}")
def get_spec(chart_id):
    path = BASE_DIR / chart_id / "spec.json"
    if not path.exists():
        raise HTMLResponse(status_code=503, details="Can't load spec.json file.")
    
    return json.loads(path.read_text())

@app.get("/{chart_id}", response_class=HTMLResponse)
def view_chart(chart_id: str):
    chart_dir = BASE_DIR / chart_id

    if not chart_dir.exists():
        raise HTTPException(status_code=678, detail="Chart not found.")

    meta = json.loads((chart_dir / "meta.json").read_text())

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chart {chart_id}</title>
    </head>
    <body>
        <p>Chart ID: {chart_id}</p>
        <p><strong>Question:</strong> {meta["question"]}</p>

        <img src="image/{chart_id}" style="max-width: 500px; max-height: 400px;" />

        <h2>Vega-Lite Spec</h2>
        <pre>{json.dumps(json.loads((chart_dir / "spec.json").read_text()), indent=2)}</pre>
    </body>
    </html>
    """

    return HTMLResponse(html)

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <h1>Vega-Lite Chart API</h1>
    <p>POST /chart to generate a chart.</p>
    <p>Then visit /{id} to view it.</p>
    """

#---- Old way (no langchain) ----
'''
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import requests
from jsonschema import validate
import vl_convert as vlc
from uuid import uuid4
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path

load_dotenv()
FPT_API_KEY = os.getenv("FPT_CLOUD_API_KEY")
print(FPT_API_KEY)
API_URL = "https://mkp-api.fptcloud.com/v1/chat/completions"
MODEL_NAME = "Qwen2.5-Coder-32B-Instruct"
VEGALITE_SCHEMA_URL = "https://vega.github.io/schema/vega-lite/v6.json"

headers = {
    "Authorization": f"Bearer {FPT_API_KEY}",
    "Content-Type": "application/json",
    }

SYSTEM_PROMPT = """
You are a good data visualisation assistant

Your task:
- Generate a valid Vega-Lite v6 JSON specification
- Use the provided data as a named data source
- Choose the most appropriate chart type for the data if user doesn't ask for a specific type of chart.
Otherwise, choose the chart in accordance to the user's query.
- Output only valid JSON

Rules:
- Vega-Lite schema: https://vega.github.io/schema/vega-lite/v6.json
- Always use: "data": { "name": "input_data" }
- Encoding fields MUST EXIST in the data
- Every encoding must specify a type


"""
app = FastAPI(title="VegaLite Data Visualisation")

#------ Request -------
class ChartRequest(BaseModel):
    data: list
    question: str

# ----- LLM call ------
def generate_vegalite_json(data, question):
    user_prompt = f"""
Data: {json.dumps(data, ensure_ascii=False)}
{SYSTEM_PROMPT}
User Question: {question}

Generate Vega-Lite v6 JSON

"""
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", 
             "content": user_prompt}
             ],
            "system_prompt": "",
            "streaming": False,
            "temperature": 1,
            "max_tokens": 1024,
            "top_p": 1, #nucleus sampling
            "top_k": 40, #top-k sampling
            "presence_penalty": 0, #penalize new topic
            "frequency_penalty": 0, #penalize frequent topics
        }
    
    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    print(response.text)

    if response.status_code != 200:
        raise HTTPException(status_code=501, detail=f"LLM Error: {response.text}")
    
    content = response.json()["choices"][0]["message"]["content"]
    #print(json.loads(content))
    content = extract_json(content)
    print(content)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="LLM did not return a valid JSON")

#------ Attach Named Data -------
def attach_data(spec, data):
    spec["datasets"] = {
        "input_data": data,
    }
    return spec

def extract_json(content: str):
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.strip().startswith("json"):
            content = content.strip()[4:]
    return content.strip()

# ----- Validate that it is VegaLite JSON ------
def validate_vegalite(spec):
    schema = requests.get(VEGALITE_SCHEMA_URL).json()
    validate(instance=spec, schema=schema)

# --- From VegaLite JSON to image ---
def generate_image_bytes(spec):
    png_image_bytes= vlc.vegalite_to_png(json.dumps(spec), scale=2)
    return png_image_bytes

def save_png_file(png_bytes, file_path="chart.png"):
    with open(file_path, "wb") as f:
        f.write(png_bytes)

BASE_DIR = Path("charts")
BASE_DIR.mkdir(exist_ok=True)

@app.post('/chart')
def generate_chart(query: ChartRequest):
    chart_id = str(uuid4())
    chart_dir = BASE_DIR / chart_id
    chart_dir.mkdir()

    spec = generate_vegalite_json(query.data, query.question)
    spec = attach_data(spec, query.data)

    try:
        validate_vegalite(spec)
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Invalid VegaLite spec: {str(e)}")
    
    # Save files
    png_path = chart_dir / "chart.png"
    spec_path = chart_dir / "spec.json"
    meta_path = chart_dir / "meta.json"
    
    png = generate_image_bytes(spec)
    output_path = "chart.png"

    save_png_file(png, output_path)

    png_path.write_bytes(png)
    spec_path.write_text(json.dumps(spec, indent=4))
    meta_path.write_text(json.dumps({
        "id": chart_id,
        "question": query.question,
    }, indent=4))

    return {
        "id": chart_id,
        "view_url": f"/{chart_id}",
        "image_url": f"/image/{chart_id}",
        "spec_url": f"/spec/{chart_id}"
    }

@app.get("/image/{chart_id}")
def get_image(chart_id):
    path = BASE_DIR / chart_id / "chart.png"
    if not path.exists():
        raise HTTPException(status_code=502, detail="Image doesn't exits.")

    return FileResponse(path, media_type="image/png")

@app.get("/spec/{chart_id}")
def get_spec(chart_id):
    path = BASE_DIR / chart_id / "spec.json"
    if not path.exists():
        raise HTMLResponse(status_code=503, details="Can't load spec.json file.")
    
    return json.loads(path.read_text())

@app.get("/{chart_id}", response_class=HTMLResponse)
def view_chart(chart_id: str):
    chart_dir = BASE_DIR / chart_id

    if not chart_dir.exists():
        raise HTTPException(status_code=504, detail="Chart not found.")

    meta = json.loads((chart_dir / "meta.json").read_text())

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chart {chart_id}</title>
    </head>
    <body>
        <p>Chart ID: {chart_id}</p>
        <p><strong>Question:</strong> {meta["question"]}</p>

        <img src="image/{chart_id}" style="max-width: 500px; max-height: 400px;" />

        <h2>Vega-Lite Spec</h2>
        <pre>{json.dumps(json.loads((chart_dir / "spec.json").read_text()), indent=2)}</pre>
    </body>
    </html>
    """

    return HTMLResponse(html)

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <h1>Vega-Lite Chart API</h1>
    <p>POST /chart to generate a chart.</p>
    <p>Then visit /{id} to view it.</p>
    """
'''