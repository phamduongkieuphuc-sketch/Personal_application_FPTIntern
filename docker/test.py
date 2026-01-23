# import plotly.express as px
# import json

# with open("victoria.geojson") as f:
#     geojson = json.load(f)

# fig = px.choropleth_mapbox(
#     geojson=geojson,
#     locations=["Victoria"],
#     featureidkey="properties.name",
#     color=[1],
#     center={"lat": -37.8, "lon": 144.9},
#     zoom=5,
#     mapbox_style="carto-positron"
# )

# fig.show()


# fig.update_geos(
#     fitbounds="locations",
#     visible=False
# )

# fig.update_traces(
#     marker_line_width=1,
#     marker_line_color="black"
# )

# fig.show()

# import json
# from collections.abc import Iterable

# def count_coords(coords):
#     """
#     Recursively count (lon, lat) coordinate pairs
#     """
#     # A single coordinate: [lon, lat] or [lon, lat, z]
#     if (
#         isinstance(coords, list)
#         and len(coords) >= 2
#         and isinstance(coords[0], (int, float))
#         and isinstance(coords[1], (int, float))
#     ):
#         return 1

#     # Otherwise, recurse deeper
#     if isinstance(coords, Iterable):
#         return sum(count_coords(c) for c in coords)

#     return 0


# # Load GeoJSON
# with open("victoria.geojson", "r", encoding="utf-8") as f:
#     geojson = json.load(f)

# total_coords = 0

# for feature in geojson.get("features", []):
#     geometry = feature.get("geometry")
#     if geometry and "coordinates" in geometry:
#         total_coords += count_coords(geometry["coordinates"])

# print(f"Total (lon, lat) coordinate pairs: {total_coords}")

import json
import psycopg2
from shapely.geometry import shape
from shapely.wkt import dumps as wkt_dumps

conn = psycopg2.connect(
    dbname="gisdb",
    user="gisuser",
    password="gispass",
    host="localhost",
    port=5432,
)
cur = conn.cursor()

with open("victoria.geojson", "r", encoding="utf-8") as f:
    geojson = json.load(f)

sql = """
INSERT INTO cities (name, population, geom)
VALUES (%s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326))
"""

inserted = 0

for feature in geojson["features"]:
    geom_type = feature["geometry"]["type"]

    # ONLY polygons
    if geom_type not in ("Polygon", "MultiPolygon"):
        continue

    geom = shape(feature["geometry"])
    geom_wkt = wkt_dumps(geom)

    props = feature.get("properties", {})
    name = props.get("name")
    population = props.get("population")

    cur.execute(sql, (name, population, geom_wkt))
    inserted += 1

conn.commit()
cur.close()
conn.close()

print(f"Inserted {inserted} polygon/multipolygon geometries.")


