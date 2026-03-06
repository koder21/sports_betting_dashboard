"""Weather service for game conditions and impact analysis using Open-Meteo API."""
import aiohttp
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
import math

VENUE_COORDINATES = {
    # NFL (outdoor only)
    "metlife stadium": (40.8128, -74.0742),
    "lambeau field": (44.5013, -88.0622),
    "soldier field": (41.8623, -87.6167),
    "arrowhead stadium": (39.0489, -94.4839),
    "gillette stadium": (42.0909, -71.2643),
    "lumen field": (47.5952, -122.3316),
    "nissan stadium": (36.1665, -86.7713),
    "acrisure stadium": (40.4468, -80.0158),
    "bank of america stadium": (35.2258, -80.8529),
    "m&t bank stadium": (39.2780, -76.6228),
    "raymond james stadium": (27.9760, -82.5034),
    "empower field at mile high": (39.7439, -105.0201),
    "levi's stadium": (37.4030, -121.9700),
    "lincoln financial field": (39.9008, -75.1675),
    "firstenergy stadium": (41.5061, -81.6995),
    "paul brown stadium": (39.0954, -84.5160),
    "highmark stadium": (42.7738, -78.7869),
    "fedex field": (38.9076, -76.8645),
    #MLB (outdoor only)
    "fenway park": (42.3467, -71.0972),
    "yankee stadium": (40.8296, -73.9262),
    "wrigley field": (41.9484, -87.6553),
    "dodger stadium": (34.0739, -118.2400),
    "oracle park": (37.7786, -122.3892),
    "citi field": (40.7571, -73.8458),
    "pnc park": (40.4469, -80.0058),
    "busch stadium": (38.6226, -90.1924),
    "coors field": (39.7558, -104.9942),
    "kauffman stadium": (39.0514, -94.4800),
    "target field": (44.9817, -93.2775),
    "globe life field": (32.7473, -97.0945),
    "petco park": (32.7072, -117.1564),
    "t-mobile park": (47.5914, -122.3325),
    "guaranteed rate field": (41.8300, -87.6339),
    "minute maid park": (29.7572, -95.3555),
    "progressive field": (41.4962, -81.6852),
    "great american ball park": (39.0975, -84.5071),
    "nationals park": (38.8730, -77.0074),
    "camden yards": (39.2830, -76.6219),
    "angel stadium": (33.8003, -117.8827),
    "citizens bank park": (39.9050, -75.1667),
    "oakland coliseum": (37.7516, -122.2005),
    "suntrust park": (33.8908, -84.4677),
    # NCAAF (major outdoor venues)
    "kinnick stadium": (41.6588, -91.5513),
    "husky stadium": (47.6503, -122.3018),
    "spartan stadium": (42.7282, -84.4850),
    "camp randall stadium": (43.0699, -89.4128),
    "donald w. reynolds razorback stadium": (36.0681, -94.1793),
    "williams-brice stadium": (33.9731, -81.0193),
    "gaylord family oklahoma memorial stadium": (35.2059, -97.4424),
    "notre dame stadium": (41.6984, -86.2340),
    "memorial stadium (clemson)": (34.6786, -82.8439),
    "michigan stadium": (42.2658, -83.7487),
    "ohio stadium": (40.0017, -83.0197),
    "beaver stadium": (40.8122, -77.8561),
    "bryant-denny stadium": (33.2083, -87.5505),
    "tiger stadium": (30.4122, -91.1839),
    "rose bowl": (34.1614, -118.1675),
}


@dataclass
class WeatherData:
    """Weather information for a game."""
    temp: Optional[float]
    wind_speed: Optional[float]
    wind_direction: Optional[str]
    humidity: Optional[float]
    precipitation: Optional[float]
    condition: Optional[str]
    feels_like: Optional[float]
    
    def is_harsh(self) -> bool:
        """Determine if weather is harsh for outdoor games."""
        harsh_factors = 0
        if self.wind_speed and self.wind_speed > 15:
            harsh_factors += 1
        if self.precipitation and self.precipitation > 0:
            harsh_factors += 1
        if self.temp and (self.temp < 32 or self.temp > 95):
            harsh_factors += 1
        return harsh_factors >= 2
    
    def impact_on_overs(self) -> float:
        """
        Return adjustment factor for over/under.
        < 1.0 suggests lower scoring (harsh weather)
        > 1.0 suggests higher scoring (favorable weather)
        """
        factor = 1.0
        
        # Wind reduces passing game accuracy and distance
        if self.wind_speed and self.wind_speed > 15:
            factor *= 0.95
        elif self.wind_speed and self.wind_speed > 25:
            factor *= 0.90
            
        # Heavy rain reduces scoring
        if self.precipitation and self.precipitation > 0.5:
            factor *= 0.92
            
        # Extreme cold reduces offensive output
        if self.temp and self.temp < 20:
            factor *= 0.96
            
        return factor


class WeatherService:
    """Manages weather data and impact analysis using Open-Meteo API (free, no key needed)."""
    
    def __init__(self):
        self.base_url = "https://api.open-meteo.com/v1/forecast"
        self.cache: Dict[str, WeatherData] = {}
    
    def _get_venue_coordinates(self, venue: str, city: Optional[str] = None) -> Optional[Tuple[float, float]]:
        """Get lat/lon for a venue from predefined list."""
        venue_key = venue.lower().strip()
        return VENUE_COORDINATES.get(venue_key)
    
    async def get_weather_for_venue(self, venue: str, city: Optional[str] = None, 
                                   game_time: Optional[datetime] = None) -> Optional[WeatherData]:
        """Fetch weather forecast for a game venue using Open-Meteo."""
        coords = self._get_venue_coordinates(venue, city)
        if not coords:
            return None
        
        cache_key = f"{venue}_{city}_{game_time}".lower()
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            lat, lon = coords
            async with aiohttp.ClientSession() as session:
                params: Dict[str, Any] = {
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "temperature_2m,relativehumidity_2m,precipitation,windspeed_10m,winddirection_10m,apparent_temperature",
                    "temperature_unit": "fahrenheit",
                    "windspeed_unit": "mph",
                    "precipitation_unit": "mm",
                    "timezone": "America/New_York",
                    "forecast_days": 7
                }
                
                async with session.get(self.base_url, params=params) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    weather = self._parse_open_meteo_response(data, game_time)
                    if weather:
                        self.cache[cache_key] = weather
                    return weather
        except Exception as e:
            print(f"Open-Meteo API error: {e}")
            return None
    
    def _parse_open_meteo_response(self, data: Dict[str, Any], game_time: Optional[datetime] = None) -> Optional[WeatherData]:
        """Parse Open-Meteo API response."""
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        
        if not times:
            return None
        
        # Find the closest time index to game_time, or use current hour
        target_index = 0
        if game_time:
            target_time_str = game_time.strftime("%Y-%m-%dT%H:00")
            try:
                target_index = times.index(target_time_str)
            except ValueError:
                # If exact match not found, use first available
                target_index = 0
        
        # Extract data for target hour
        temps = hourly.get("temperature_2m", [])
        humidities = hourly.get("relativehumidity_2m", [])
        precips = hourly.get("precipitation", [])
        wind_speeds = hourly.get("windspeed_10m", [])
        wind_dirs = hourly.get("winddirection_10m", [])
        feels_likes = hourly.get("apparent_temperature", [])
        
        if target_index >= len(temps):
            target_index = 0
        
        temp = temps[target_index] if temps else None
        humidity = humidities[target_index] if humidities else None
        precipitation = precips[target_index] if precips else None
        wind_speed = wind_speeds[target_index] if wind_speeds else None
        wind_deg = wind_dirs[target_index] if wind_dirs else None
        feels_like = feels_likes[target_index] if feels_likes else None
        
        # Determine condition from precipitation
        if precipitation and precipitation > 0.5:
            condition = "Rainy"
        elif precipitation and precipitation > 0:
            condition = "Light Rain"
        else:
            condition = "Clear"
        
        return WeatherData(
            temp=temp,
            wind_speed=wind_speed,
            wind_direction=self._get_wind_direction(wind_deg),
            humidity=humidity,
            precipitation=precipitation,
            condition=condition,
            feels_like=feels_like
        )
    
    @staticmethod
    def _get_wind_direction(degrees: Optional[float]) -> Optional[str]:
        """Convert wind degrees to cardinal direction."""
        if degrees is None:
            return None
        
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        idx = round(degrees / 22.5) % 16
        return directions[idx]
    
    async def get_weather_impact_on_game(self, 
                                        venue: str, 
                                        sport: str,
                                        city: Optional[str] = None,
                                        game_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get weather impact analysis for specific sport."""
        weather = await self.get_weather_for_venue(venue, city, game_time)
        
        if not weather:
            return {"weather": None, "impact": None}
        
        impact: Dict[str, Any] = {
            "weather": {
                "temp": weather.temp,
                "wind_speed": weather.wind_speed,
                "wind_direction": weather.wind_direction,
                "humidity": weather.humidity,
                "precipitation": weather.precipitation,
                "condition": weather.condition,
                "feels_like": weather.feels_like,
                "is_harsh": weather.is_harsh()
            },
            "impact": {
                "is_harsh_conditions": weather.is_harsh()
            }
        }
        
        # Sport-specific impacts
        if sport.upper() in ["NFL", "NCAAF"]:
            impact["impact"]["overs_adjustment"] = weather.impact_on_overs()
            impact["impact"]["passing_game_affected"] = weather.wind_speed and weather.wind_speed > 15
            impact["impact"]["kicking_affected"] = weather.wind_speed and weather.wind_speed > 20
            impact["impact"]["recommendation"] = self._get_football_recommendation(weather)
        
        elif sport.upper() in ["NBA", "NCAAB"]:
            # Indoor sport, minimal weather impact
            impact["impact"]["weather_impact_minimal"] = True
        
        elif sport.upper() == "MLB":
            impact["impact"]["overs_adjustment"] = weather.impact_on_overs()
            impact["impact"]["wind_helps_hitters"] = weather.wind_direction in ["O", "Out"]
            impact["impact"]["recommendation"] = self._get_baseball_recommendation(weather)
        
        return impact
    
    @staticmethod
    def _get_football_recommendation(weather: WeatherData) -> str:
        """Get betting recommendation for football based on weather."""
        if weather.wind_speed and weather.wind_speed > 25:
            return "Harsh wind: favor running game, under-heavy lineups"
        elif weather.precipitation and weather.precipitation > 0.5:
            return "Heavy rain: expect low-scoring, defensive game"
        elif weather.temp and weather.temp < 20:
            return "Cold conditions: may slow offensive pace"
        else:
            return "Normal weather conditions"
    
    @staticmethod
    def _get_baseball_recommendation(weather: WeatherData) -> str:
        """Get betting recommendation for baseball based on weather."""
        if weather.temp and weather.temp > 85:
            return "Hot day game: ball carries further, favor overs"
        elif weather.wind_direction == "Out":
            return "Wind blowing out: favor overs"
        elif weather.wind_direction == "In":
            return "Wind blowing in: favor unders"
        else:
            return "Normal weather conditions"