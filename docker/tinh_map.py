import json
from shapely import wkb
from shapely.geometry import mapping
import plotly.express as plx
from uuid import uuid4
from pathlib import Path

BASE_DIR = Path("Map Tinh")
BASE_DIR.mkdir(exist_ok=True)

chart_id = str(uuid4())


with open("tinh_map.json") as f:
    tinh_map = json.load(f)

cols = tinh_map["columns"]
rows = tinh_map["data"]

name_idx = cols.index("tentinh")
geom_idx = cols.index("geom")

features = []

for row in rows:
    name = row[name_idx]
    geom_wkb_hex = row[geom_idx]

    geom = wkb.loads(bytes.fromhex(geom_wkb_hex))

    features.append({
        "type": "Feature",
        "properties": {"name": name},
        "geometry": mapping(geom)
    })

geo_json = {
    "type": "FeatureCollection",
    "features": features
}

fig = plx.choropleth_mapbox(
    geojson=geo_json,
    locations=[f["properties"]["name"] for f in features],
    featureidkey="properties.name",
    color_discrete_sequence=["maroon"],
    mapbox_style="open-street-map",
    zoom=4.7,
    center={"lat":16,"lon":108}
)

image_path = BASE_DIR / f"chart_{chart_id}.png"

fig.update_layout(
    margin=dict(l=40, r=40, t=60, b=60),
    coloraxis_showscale=False,
    title_text="Bản đồ Tỉnh Việt Nam"
)

fig.write_image(
    image_path,
    width=1200,
    height=1000,
    scale=5
)

fig.show()



