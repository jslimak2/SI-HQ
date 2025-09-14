"""
Weather API Integration for LSTM Models
Provides real weather data for outdoor sports prediction
"""
import os
import time
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json
from enum import Enum

logger = logging.getLogger(__name__)


class WeatherCondition(Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    SNOW = "snow"
    STORM = "storm"
    FOG = "fog"


@dataclass
class WeatherData:
    """Weather data structure for game prediction"""
    temperature_f: float
    humidity_percent: float
    wind_speed_mph: float
    wind_direction: str
    precipitation_chance: float
    precipitation_amount: float
    pressure_mb: float
    visibility_miles: float
    condition: WeatherCondition
    is_dome: bool = False
    location: str = ""
    timestamp: datetime = None


@dataclass
class GameLocation:
    """Game location information"""
    city: str
    state: str
    venue: str
    latitude: float
    longitude: float
    is_dome: bool = False
    
    
class WeatherAPIProvider:
    """Base weather API provider"""
    
    def get_weather_for_location(self, location: GameLocation, game_time: datetime) -> Optional[WeatherData]:
        raise NotImplementedError
        
    def get_historical_weather(self, location: GameLocation, date: datetime) -> Optional[WeatherData]:
        raise NotImplementedError


class OpenWeatherMapProvider(WeatherAPIProvider):
    """OpenWeatherMap API provider for weather data"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.session = requests.Session()
        
    def get_weather_for_location(self, location: GameLocation, game_time: datetime) -> Optional[WeatherData]:
        """Get current or forecast weather for a game location"""
        try:
            # Check if it's a dome venue (indoor)
            if location.is_dome:
                return WeatherData(
                    temperature_f=72.0,
                    humidity_percent=50.0,
                    wind_speed_mph=0.0,
                    wind_direction="N/A",
                    precipitation_chance=0.0,
                    precipitation_amount=0.0,
                    pressure_mb=1013.25,
                    visibility_miles=10.0,
                    condition=WeatherCondition.CLEAR,
                    is_dome=True,
                    location=f"{location.city}, {location.state}",
                    timestamp=datetime.now()
                )
            
            # Determine if we need current weather or forecast
            hours_until_game = (game_time - datetime.now()).total_seconds() / 3600
            
            if hours_until_game <= 0:
                # Historical weather (use current as proxy)
                return self._get_current_weather(location)
            elif hours_until_game <= 120:  # Within 5 days
                return self._get_forecast_weather(location, game_time)
            else:
                # Too far in future, use historical average
                return self._get_historical_average(location, game_time)
                
        except Exception as e:
            logger.error(f"Failed to get weather for {location.city}: {e}")
            return self._get_fallback_weather(location)
            
    def _get_current_weather(self, location: GameLocation) -> Optional[WeatherData]:
        """Get current weather conditions"""
        try:
            url = f"{self.base_url}/weather"
            params = {
                'lat': location.latitude,
                'lon': location.longitude,
                'appid': self.api_key,
                'units': 'imperial'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_weather_data(data, location)
            
        except Exception as e:
            logger.error(f"Failed to get current weather: {e}")
            return None
            
    def _get_forecast_weather(self, location: GameLocation, game_time: datetime) -> Optional[WeatherData]:
        """Get forecast weather for game time"""
        try:
            url = f"{self.base_url}/forecast"
            params = {
                'lat': location.latitude,
                'lon': location.longitude,
                'appid': self.api_key,
                'units': 'imperial'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Find closest forecast to game time
            forecasts = data.get('list', [])
            closest_forecast = None
            min_time_diff = float('inf')
            
            for forecast in forecasts:
                forecast_time = datetime.fromtimestamp(forecast['dt'])
                time_diff = abs((forecast_time - game_time).total_seconds())
                
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_forecast = forecast
                    
            if closest_forecast:
                return self._parse_weather_data(closest_forecast, location)
                
        except Exception as e:
            logger.error(f"Failed to get forecast weather: {e}")
            
        return None
        
    def _get_historical_average(self, location: GameLocation, game_time: datetime) -> WeatherData:
        """Get historical weather average for the date/location"""
        # This is a simplified implementation
        # In production, you'd use historical weather API or database
        
        month = game_time.month
        
        # Rough temperature estimates by month and region
        temp_estimates = {
            1: 35, 2: 40, 3: 50, 4: 60, 5: 70, 6: 80,
            7: 85, 8: 83, 9: 75, 10: 65, 11: 50, 12: 40
        }
        
        # Adjust for location (very simplified)
        base_temp = temp_estimates.get(month, 65)
        if 'FL' in location.state or 'TX' in location.state or 'AZ' in location.state:
            base_temp += 10
        elif 'MN' in location.state or 'WI' in location.state or 'ME' in location.state:
            base_temp -= 15
            
        return WeatherData(
            temperature_f=float(base_temp),
            humidity_percent=60.0,
            wind_speed_mph=8.0,
            wind_direction="SW",
            precipitation_chance=30.0,
            precipitation_amount=0.0,
            pressure_mb=1013.25,
            visibility_miles=10.0,
            condition=WeatherCondition.CLOUDY,
            is_dome=location.is_dome,
            location=f"{location.city}, {location.state}",
            timestamp=datetime.now()
        )
        
    def _parse_weather_data(self, data: Dict, location: GameLocation) -> WeatherData:
        """Parse OpenWeatherMap API response"""
        main = data.get('main', {})
        weather = data.get('weather', [{}])[0]
        wind = data.get('wind', {})
        
        # Map weather conditions
        weather_id = weather.get('id', 800)
        if weather_id < 300:
            condition = WeatherCondition.STORM
        elif weather_id < 600:
            condition = WeatherCondition.RAIN
        elif weather_id < 700:
            condition = WeatherCondition.SNOW
        elif weather_id < 800:
            condition = WeatherCondition.FOG
        elif weather_id == 800:
            condition = WeatherCondition.CLEAR
        else:
            condition = WeatherCondition.CLOUDY
            
        return WeatherData(
            temperature_f=main.get('temp', 70.0),
            humidity_percent=main.get('humidity', 50.0),
            wind_speed_mph=wind.get('speed', 0.0),
            wind_direction=self._wind_direction_from_degrees(wind.get('deg', 0)),
            precipitation_chance=data.get('clouds', {}).get('all', 0.0),
            precipitation_amount=data.get('rain', {}).get('1h', 0.0) or data.get('snow', {}).get('1h', 0.0),
            pressure_mb=main.get('pressure', 1013.25),
            visibility_miles=data.get('visibility', 10000) / 1609.34,  # Convert m to miles
            condition=condition,
            is_dome=location.is_dome,
            location=f"{location.city}, {location.state}",
            timestamp=datetime.now()
        )
        
    def _wind_direction_from_degrees(self, degrees: float) -> str:
        """Convert wind degrees to cardinal direction"""
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = int((degrees + 11.25) / 22.5) % 16
        return directions[index]
        
    def _get_fallback_weather(self, location: GameLocation) -> WeatherData:
        """Fallback weather data when API fails"""
        return WeatherData(
            temperature_f=70.0,
            humidity_percent=50.0,
            wind_speed_mph=5.0,
            wind_direction="SW",
            precipitation_chance=20.0,
            precipitation_amount=0.0,
            pressure_mb=1013.25,
            visibility_miles=10.0,
            condition=WeatherCondition.CLEAR,
            is_dome=location.is_dome,
            location=f"{location.city}, {location.state}",
            timestamp=datetime.now()
        )
        
    def get_historical_weather(self, location: GameLocation, date: datetime) -> Optional[WeatherData]:
        """Get historical weather data (simplified implementation)"""
        return self._get_historical_average(location, date)


class WeatherService:
    """Main weather service for sports predictions"""
    
    def __init__(self):
        self.provider = None
        self.venue_locations = self._load_venue_locations()
        self.logger = logging.getLogger(__name__)
        
        # Initialize weather API provider
        weather_api_key = os.getenv('WEATHER_API_KEY')
        if weather_api_key and weather_api_key != 'your_production_weather_api_key':
            self.provider = OpenWeatherMapProvider(weather_api_key)
            self.logger.info("Weather API provider initialized")
        else:
            self.logger.warning("No weather API key configured, using fallback data")
            
    def _load_venue_locations(self) -> Dict[str, GameLocation]:
        """Load venue location data"""
        # In production, this would come from a database
        # For now, return some common venues
        return {
            # NFL venues
            'Lambeau Field': GameLocation('Green Bay', 'WI', 'Lambeau Field', 44.5013, -88.0622, False),
            'Soldier Field': GameLocation('Chicago', 'IL', 'Soldier Field', 41.8623, -87.6167, False),
            'MetLife Stadium': GameLocation('East Rutherford', 'NJ', 'MetLife Stadium', 40.8128, -74.0742, False),
            'Mercedes-Benz Superdome': GameLocation('New Orleans', 'LA', 'Mercedes-Benz Superdome', 29.9511, -90.0812, True),
            'Ford Field': GameLocation('Detroit', 'MI', 'Ford Field', 42.3400, -83.0456, True),
            
            # MLB venues
            'Fenway Park': GameLocation('Boston', 'MA', 'Fenway Park', 42.3467, -71.0972, False),
            'Wrigley Field': GameLocation('Chicago', 'IL', 'Wrigley Field', 41.9484, -87.6553, False),
            'Yankee Stadium': GameLocation('Bronx', 'NY', 'Yankee Stadium', 40.8296, -73.9262, False),
            'Minute Maid Park': GameLocation('Houston', 'TX', 'Minute Maid Park', 29.7572, -95.3555, True),
            'Tropicana Field': GameLocation('St. Petersburg', 'FL', 'Tropicana Field', 27.7682, -82.6534, True),
            
            # NBA venues (mostly indoor, but included for completeness)
            'Madison Square Garden': GameLocation('New York', 'NY', 'Madison Square Garden', 40.7505, -73.9934, True),
            'Staples Center': GameLocation('Los Angeles', 'CA', 'Staples Center', 34.0430, -118.2673, True),
            'United Center': GameLocation('Chicago', 'IL', 'United Center', 41.8807, -87.6742, True)
        }
        
    def get_weather_for_game(self, venue: str, game_time: datetime) -> Optional[WeatherData]:
        """Get weather data for a specific game"""
        location = self.venue_locations.get(venue)
        
        if not location:
            # Try to find location by partial match
            for venue_name, venue_location in self.venue_locations.items():
                if venue.lower() in venue_name.lower() or venue_name.lower() in venue.lower():
                    location = venue_location
                    break
                    
        if not location:
            self.logger.warning(f"Unknown venue: {venue}")
            # Create a generic location
            location = GameLocation('Unknown', 'XX', venue, 40.0, -95.0, False)
            
        if self.provider:
            weather_data = self.provider.get_weather_for_location(location, game_time)
            if weather_data:
                return weather_data
                
        # Fallback to synthetic weather
        return self._generate_synthetic_weather(location, game_time)
        
    def _generate_synthetic_weather(self, location: GameLocation, game_time: datetime) -> WeatherData:
        """Generate synthetic weather data when API is unavailable"""
        import random
        
        if location.is_dome:
            return WeatherData(
                temperature_f=72.0,
                humidity_percent=50.0,
                wind_speed_mph=0.0,
                wind_direction="N/A",
                precipitation_chance=0.0,
                precipitation_amount=0.0,
                pressure_mb=1013.25,
                visibility_miles=10.0,
                condition=WeatherCondition.CLEAR,
                is_dome=True,
                location=f"{location.city}, {location.state}",
                timestamp=datetime.now()
            )
            
        # Generate random but realistic weather
        month = game_time.month
        
        # Base temperature by month
        if month in [12, 1, 2]:  # Winter
            temp_range = (25, 45)
        elif month in [3, 4, 5]:  # Spring
            temp_range = (45, 70)
        elif month in [6, 7, 8]:  # Summer
            temp_range = (65, 85)
        else:  # Fall
            temp_range = (40, 65)
            
        temperature = random.uniform(*temp_range)
        
        return WeatherData(
            temperature_f=temperature,
            humidity_percent=random.uniform(30, 80),
            wind_speed_mph=random.uniform(0, 20),
            wind_direction=random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
            precipitation_chance=random.uniform(0, 50),
            precipitation_amount=random.uniform(0, 0.5) if random.random() < 0.3 else 0.0,
            pressure_mb=random.uniform(990, 1030),
            visibility_miles=random.uniform(5, 10),
            condition=random.choice(list(WeatherCondition)),
            is_dome=location.is_dome,
            location=f"{location.city}, {location.state}",
            timestamp=datetime.now()
        )
        
    def get_weather_features_for_prediction(self, weather_data: WeatherData) -> Dict[str, float]:
        """Convert weather data to ML features"""
        if weather_data.is_dome:
            return {
                'is_dome': 1.0,
                'temperature_f': 72.0,
                'humidity_percent': 50.0,
                'wind_speed_mph': 0.0,
                'precipitation_chance': 0.0,
                'pressure_mb': 1013.25,
                'visibility_miles': 10.0,
                'condition_clear': 1.0,
                'condition_rain': 0.0,
                'condition_snow': 0.0,
                'condition_storm': 0.0
            }
            
        # One-hot encode weather conditions
        condition_features = {
            'condition_clear': 1.0 if weather_data.condition == WeatherCondition.CLEAR else 0.0,
            'condition_cloudy': 1.0 if weather_data.condition == WeatherCondition.CLOUDY else 0.0,
            'condition_rain': 1.0 if weather_data.condition == WeatherCondition.RAIN else 0.0,
            'condition_snow': 1.0 if weather_data.condition == WeatherCondition.SNOW else 0.0,
            'condition_storm': 1.0 if weather_data.condition == WeatherCondition.STORM else 0.0,
            'condition_fog': 1.0 if weather_data.condition == WeatherCondition.FOG else 0.0
        }
        
        return {
            'is_dome': 0.0,
            'temperature_f': weather_data.temperature_f,
            'humidity_percent': weather_data.humidity_percent,
            'wind_speed_mph': weather_data.wind_speed_mph,
            'precipitation_chance': weather_data.precipitation_chance,
            'precipitation_amount': weather_data.precipitation_amount,
            'pressure_mb': weather_data.pressure_mb,
            'visibility_miles': weather_data.visibility_miles,
            **condition_features
        }


# Global instance
weather_service = WeatherService()


def get_weather_for_game(venue: str, game_time: datetime) -> Optional[WeatherData]:
    """Convenience function to get weather for a game"""
    return weather_service.get_weather_for_game(venue, game_time)


def get_weather_features(venue: str, game_time: datetime) -> Dict[str, float]:
    """Get weather features for ML prediction"""
    weather_data = get_weather_for_game(venue, game_time)
    if weather_data:
        return weather_service.get_weather_features_for_prediction(weather_data)
    else:
        # Return default features if weather unavailable
        return {
            'is_dome': 0.0,
            'temperature_f': 70.0,
            'humidity_percent': 50.0,
            'wind_speed_mph': 5.0,
            'precipitation_chance': 20.0,
            'precipitation_amount': 0.0,
            'pressure_mb': 1013.25,
            'visibility_miles': 10.0,
            'condition_clear': 1.0,
            'condition_cloudy': 0.0,
            'condition_rain': 0.0,
            'condition_snow': 0.0,
            'condition_storm': 0.0,
            'condition_fog': 0.0
        }