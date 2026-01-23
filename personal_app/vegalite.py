import vl_convert as vlc
from fastapi import FastAPI
from fastapi.responses import Response

app = FastAPI()

'''vegalite_json = {
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "description": "A simple bar chart with embedded data.",
  "data": {
    "values": [
      {"a": "A", "b": 28}, {"a": "B", "b": 55}, {"a": "C", "b": 43},
      {"a": "D", "b": 91}, {"a": "E", "b": 81}, {"a": "F", "b": 53},
      {"a": "G", "b": 19}, {"a": "H", "b": 87}, {"a": "I", "b": 52}
    ]
  },
  "mark": "bar",
  "encoding": {
    "x": {"field": "a", "type": "nominal", "axis": {"labelAngle": 0}},
    "y": {"field": "b", "type": "quantitative"}
  }
}

png_bytes = vlc.vegalite_to_png(vegalite_json)

with open("chart.png", "wb") as f:
    f.write(png_bytes)
    '''

@app.post("/render", response_class=Response)
def render_chart(spec: dict):
    png = vlc.vegalite_to_png(spec)
    return Response(content=png, media_type="image/png")


"""
# ----------Vegalite JSON FILE -> PNG--------------

import json
import vl_concert as vlc

with open("chart.json") as f:
    vegalite_json = json.load(f)

png = vlc.vegalite_to_png(vegalite_json)

with open("chart.png", "wb") as f:
    f.write(png)
"""