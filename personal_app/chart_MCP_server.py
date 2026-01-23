from mcp.server.fastmcp import FastMCP
from uuid import uuid4
from typing import Any, Dict, List
from pathlib import Path
import json
from vega_json_gen import generate_vegalite_json, attach_data, validate_vegalite, generate_image_bytes
from draw_bubchart import create_bubble_chart

mcp = FastMCP("Chart Generator's Server")
BASE_DIR = Path("charts")
BASE_DIR.mkdir(exist_ok=True)

@mcp.tool()
def vegalite_chart(data: List[Dict[str, Any]], question: str) -> Dict[str, Any]:
    chart_id = str(uuid4())
    chart_dir = BASE_DIR / chart_id
    chart_dir.mkdir(exist_ok=False)

    spec = generate_vegalite_json(data, question)
    spec = attach_data(spec, data)
    validate_vegalite(spec)

    image_bytes = generate_image_bytes(spec)
    (chart_dir / "chart.png").write_bytes(image_bytes)
    (chart_dir / "spec.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False))

    return {
        "id": chart_id,
        "type": "vegalite",
        "image": str(chart_dir / "chart.png"),
        "spec": str(chart_dir / "spec.json")
    }

@mcp.tool()
def plotly_chart(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    chart_id = str(uuid4())
    chart_dir = BASE_DIR / chart_id
    chart_dir.mkdir(exist_ok=False)

    fig = create_bubble_chart(data)
    fig.write_image(
        chart_dir / "chart.png",
        width=1200,
        height=700,
        scale=2,
    )

    return {
        "id": chart_id,
        "type": "plotly",
        "image": str(chart_dir / "chart.png"),
    }

if __name__ == "__main__":
    mcp.run()