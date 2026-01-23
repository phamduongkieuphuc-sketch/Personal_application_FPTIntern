import geopandas as gpd
from sqlalchemy import create_engine
import plotly.express as plx
from uuid import uuid4
from pathlib import Path
import json
import plotly.graph_objects as go

engine = create_engine("postgresql://gisuser:gispass@localhost:5432/gisdb")

# Load in coords data
data = gpd.read_postgis(
    "SELECT name, population, geom FROM cities",
    con=engine,
    geom_col="geom"
)

#WGS84 / EPSG:4326 is the standard global coordinate system
gdf = data.to_crs(epsg=4326)

points = gdf[gdf.geometry.type == "Point"].copy()
print(f"Point: {points}")
polygons = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
print(f"Point: {polygons}")
print(f"Name to draw polygon: {polygons.index}")
polygons_geojson = json.loads(polygons.to_json())

points["lon"] = points.geometry.x
points["lat"] = points.geometry.y
minx, miny, maxx, maxy = gdf.total_bounds
center_lat = (miny + maxy) / 2
center_lon = (minx + maxx) / 2

lon_range = maxx - minx

if lon_range < 0.1:
    zoom = 10
elif lon_range < 1:
    zoom = 7
elif lon_range < 5:
    zoom = 5
elif lon_range < 10:
    zoom = 4
else:
    zoom = 3


figure_points = plx.scatter_mapbox(
    points,
    lon="lon",
    lat="lat",
    size="population",
    color="population",
    hover_name="name",
    zoom=2,
    height=1000
)

fig_polygons = plx.choropleth_map(
    polygons,
    geojson=polygons_geojson,
    locations=polygons["name"],
    color="population",
    hover_name="name",
    featureidkey="properties.index",
    map_style="carto-positron",
    opacity=0.5,
    zoom=4,
    center={"lat": -37.8, "lon": 144.9}
)


fig = go.Figure()

# --- POLYGONS (Victoria boundary) ---
fig.add_trace(
    go.Choroplethmapbox(
        geojson=polygons_geojson,
        locations=polygons["name"],
        z=polygons["population"],
        featureidkey="properties.name",
        colorscale="Viridis",
        marker_opacity=0.4,
        marker_line_width=2,
        hovertext=polygons["name"],
        hoverinfo="text",
        name="Boundaries"
    )
)

# --- POINTS (cities) ---
fig.add_trace(
    go.Scattermapbox(
        lat=points["lat"],
        lon=points["lon"],
        mode="markers",
        marker=dict(
            size=points["population"] / points["population"].max() * 40,
            color=points["population"],
            colorscale="Viridis",
            showscale=False
        ),
        text=points["name"],
        hoverinfo="text",
        name="Cities"
    )
)

fig.update_layout(
    mapbox_style="carto-positron",
    mapbox_zoom=2,
    mapbox_center={"lat": center_lat, "lon": center_lon},
    title="Cities and Victoria Boundary (PostGIS)",
    margin=dict(r=0, t=40, l=0, b=0)
)

output_dir = Path("Charts")
output_dir.mkdir(exist_ok=True)

file_id = uuid4()
image_path = output_dir / f"chart_{file_id}.png"

# Save image
fig.write_image(
        image_path,
        width=1200,
        height=700,
        scale=2
)

fig.show()
