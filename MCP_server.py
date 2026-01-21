from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server
import httpx

mcp = FastMCP("weather")

@mcp.tool()
async def get_forecast(location: str) -> str:
    """
    Get current weather for a city using Open-Meteo (no API key).
    """

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Get city name
        geo_resp = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 1},
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            return f"Could not find location '{location}'."

        city = geo_data["results"][0]
        lat = city["latitude"]
        lon = city["longitude"]
        country = city.get("country", "")

        # Fetch weather
        weather_resp = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
            },
        )
        weather_resp.raise_for_status()
        weather_data = weather_resp.json()

    cw = weather_data.get("current_weather", {})
    temp = cw.get("temperature")
    wind = cw.get("windspeed")

    return (
        f"Weather in {city['name']}, {country}: "
        f"{temp}°C, wind {wind} km/h"
    )

async def main():
    async with stdio_server() as (read, write):
        await mcp.run(read, write)

if __name__ == "__main__":
    mcp.run(transport="stdio")
