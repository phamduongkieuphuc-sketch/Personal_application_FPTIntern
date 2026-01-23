import folium


# Create map (center roughly where your GeoJSON is)
m = folium.Map(location=[-37.815, 144.9666], zoom_start=6)

# Add GeoJSON directly
folium.GeoJson(
    "victoria.geojson",
    name="The state of Victoria in Australia",
    style_function=lambda feature: {
        "fillColor": "blue",
        "color": "black",
        "weight": 2,
        "fillOpacity": 0.3,
    }
).add_to(m)

# Save map
m.save("city_boundary_map.html")

print("Map saved as city_boundary_map.html")
