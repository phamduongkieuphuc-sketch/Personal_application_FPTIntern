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

# import json
# import psycopg2
# from shapely.geometry import shape
# from shapely.wkt import dumps as wkt_dumps

# conn = psycopg2.connect(
#     dbname="gisdb",
#     user="gisuser",
#     password="gispass",
#     host="localhost",
#     port=5432,
# )
# cur = conn.cursor()

# with open("victoria.geojson", "r", encoding="utf-8") as f:
#     geojson = json.load(f)

# sql = """
# INSERT INTO cities (name, population, geom)
# VALUES (%s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326))
# """

# inserted = 0

# for feature in geojson["features"]:
#     geom_type = feature["geometry"]["type"]

#     # ONLY polygons
#     if geom_type not in ("Polygon", "MultiPolygon"):
#         continue

#     geom = shape(feature["geometry"])
#     geom_wkt = wkt_dumps(geom)

#     props = feature.get("properties", {})
#     name = props.get("name")
#     population = props.get("population")

#     cur.execute(sql, (name, population, geom_wkt))
#     inserted += 1

# conn.commit()
# cur.close()
# conn.close()

# print(f"Inserted {inserted} polygon/multipolygon geometries.")

import json
import vl_convert as vlc
vega_dict = {
    'id': 'ea5a6af6-c824-46ee-977d-3c46c27555f7', 
    'vegaSpec': {
        '$schema': 'https://vega.github.io/schema/vega-lite/v5.json', 'config': {'mark': {'tooltip': True}, 
        'font': 'Roboto, Arial, Noto Sans, sans-serif', 'padding': {'top': 30, 'bottom': 20, 'left': 0, 'right': 0}, 
        'title': {'color': '#262626', 'fontSize': 14}, 'axis': {'labelPadding': 0, 'labelOffset': 0, 'labelFontSize': 10, 
        'gridColor': '#d9d9d9', 'titleColor': '#434343', 'labelColor': '#65676c', 'labelFont': ' Roboto, Arial, Noto Sans, sans-serif'}, 
        'axisX': {'labelAngle': -45}, 'line': {'color': '#1570EF'}, 'bar': {'color': '#1570EF'}, 
        'legend': {'symbolLimit': 15, 'columns': 1, 'labelFontSize': 10, 'labelColor': '#65676c', 'titleColor': '#434343', 'titleFontSize': 14}, 
        'range': {'category': ['#7763CF', '#444CE7', '#1570EF', '#0086C9', '#3E4784', '#E31B54', '#EC4A0A', '#EF8D0C', '#EBC405', '#5381AD'], 
        'ordinal': ['#7763CF', '#444CE7', '#1570EF', '#0086C9', '#3E4784', '#E31B54', '#EC4A0A', '#EF8D0C', '#EBC405', '#5381AD'], 
        'diverging': ['#7763CF', '#444CE7', '#1570EF', '#0086C9', '#3E4784', '#E31B54', '#EC4A0A', '#EF8D0C', '#EBC405', '#5381AD'], 
        'symbol': ['#7763CF', '#444CE7', '#1570EF', '#0086C9', '#3E4784', '#E31B54', '#EC4A0A', '#EF8D0C', '#EBC405', '#5381AD'], 
        'heatmap': ['#7763CF', '#444CE7', '#1570EF', '#0086C9', '#3E4784', '#E31B54', '#EC4A0A', '#EF8D0C', '#EBC405', '#5381AD'], 
        'ramp': ['#7763CF', '#444CE7', '#1570EF', '#0086C9', '#3E4784', '#E31B54', '#EC4A0A', '#EF8D0C', '#EBC405', '#5381AD']}, 
        'point': {'size': 60, 'color': '#1570EF'}}, 'title': 'Số lượng sản phẩm theo loại tại Hà Nội (Product count by type in Hanoi) (Nombre de produits par type à Hanoï) (Cantidad de productos por tipo en Hanói)', 
        'data': {'values': [{'Loai_SP': 'MIP - 10DV', 'so_luong': 16665}, {'Loai_SP': 'VCX - 08', 'so_luong': 45551}]}, 
        'mark': {'type': 'bar'}, 'width': 'container', 'height': 'container', 'autosize': {'type': 'fit', 'contains': 'padding'}, 
        'encoding': {'x': {'field': 'Loai_SP', 'type': 'nominal', 'title': 'Loại sản phẩm'}, 
        'y': {'field': 'so_luong', 'type': 'quantitative', 'title': 'Số lượng'}, 
        'color': {'field': 'Loai_SP', 'type': 'nominal', 'title': 'Loại sản phẩm', 
        'scale': {'range': ['#7763CF', '#444CE7', '#1570EF', '#0086C9', '#3E4784', '#E31B54', '#EC4A0A', '#EF8D0C', '#EBC405', '#5381AD']}}, 
        'opacity': {'condition': {'param': 'hover', 'value': 1}, 'value': 0.3}}, 
        'params': [{'name': 'hover', 'select': {'type': 'point', 'on': 'mouseover', 'clear': 'mouseout', 'fields': ['Loai_SP']}}]}, 
        'threadId': 'c366871f-647f-4495-882c-adfce2c5222d'}

vega_dict['vegaSpec']['data']['values'].extend([
    {'Loai_SP': 'FTTH - Home', 'so_luong': 32000},
    {'Loai_SP': 'Camera AI', 'so_luong': 12850},
    {'Loai_SP': 'Cloud VPS', 'so_luong': 7420},
    {'Loai_SP': 'FTTH - Masion', 'so_luong': 45787},
    {'Loai_SP': 'FTTH - Villa', 'so_luong': 23009},
    {'Loai_SP': 'FTTH - Resort', 'so_luong': 58862},
    {'Loai_SP': 'FTTH - Hotel', 'so_luong': 79865},
    {'Loai_SP': 'FTTH - Club', 'so_luong': 12354},
    {'Loai_SP': 'FTTH - Pub', 'so_luong': 78521},
    {'Loai_SP': 'FTTH - Bar', 'so_luong': 10236},
    {'Loai_SP': 'FTTH - Shopping Centre', 'so_luong': 14702},
    {'Loai_SP': 'FTTH - Warehouse', 'so_luong': 96350},
    {'Loai_SP': 'FTTH - Groceries', 'so_luong': 32560},
])

# Can loai bo "width": "container", "height": "container", "autosize": {"type": "fit", "contains": "padding"} boi vi container chi phu hop cho web
# Chu se bi cut khi chuyen sang png

spec = vega_dict['vegaSpec']

# Pad giu lai content quan trong. Tao padding de tranh viec content bi cat khi chuyen sang png
spec["autosize"] = {"type": "pad", "contains": "content"}
spec["padding"] = {"top": 50, "bottom": 60, "left": 80, "right": 40}

num_bars = len(spec["data"]["values"])
spec["width"] = max(120 * num_bars, 400)
spec["height"] = 350

spec["config"]["axisX"]["labelLimit"] = 300
spec["config"]["axis"]["titleLimit"] = 400
spec["config"]["legend"]["labelLimit"] = 300


png_image_bytes= vlc.vegalite_to_png(json.dumps(vega_dict['vegaSpec']), scale=1)
with open('vega_chart.png', 'wb') as f:
    f.write(png_image_bytes)


