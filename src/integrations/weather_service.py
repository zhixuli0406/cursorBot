"""
Weather Service Integration
Provides current weather information for daily briefings
"""

import aiohttp
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from ..utils.logger import logger
from ..utils.config import settings


class WeatherService:
    """
    天氣服務
    支援多個免費天氣 API
    """

    def __init__(self):
        self.api_key = getattr(settings, "weather_api_key", "")
        self.weather_provider = getattr(settings, "weather_provider", "openweathermap").lower()
        self.default_city = getattr(settings, "weather_default_city", "Taipei")
        self.default_country = getattr(settings, "weather_default_country", "TW")
        self.language = getattr(settings, "weather_language", "zh_tw")
        self.units = getattr(settings, "weather_units", "metric")  # metric (攝氏), imperial (華氏)

    async def get_weather(
        self,
        city: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        獲取天氣信息

        Args:
            city: 城市名稱（可選，默認使用配置）
            country: 國家代碼（可選，默認使用配置）

        Returns:
            天氣數據字典，包含溫度、天氣狀況、濕度等
        """
        city = city or self.default_city
        country = country or self.default_country

        try:
            if self.weather_provider == "openweathermap":
                return await self._get_openweathermap(city, country)
            elif self.weather_provider == "weatherapi":
                return await self._get_weatherapi(city, country)
            else:
                logger.warning(f"Unknown weather provider: {self.weather_provider}")
                return None
        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            return None

    async def _get_openweathermap(self, city: str, country: str) -> Optional[Dict[str, Any]]:
        """
        使用 OpenWeatherMap API 獲取天氣
        免費計劃：60 calls/minute
        註冊：https://openweathermap.org/api
        """
        if not self.api_key:
            logger.debug("OpenWeatherMap API key not configured, skipping weather")
            return None

        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": f"{city},{country}",
            "appid": self.api_key,
            "units": self.units,
            "lang": self._get_lang_code("openweathermap"),
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_openweathermap(data)
                    else:
                        logger.warning(f"OpenWeatherMap API error: {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.warning("OpenWeatherMap API timeout")
            return None
        except Exception as e:
            logger.error(f"OpenWeatherMap API error: {e}")
            return None

    async def _get_weatherapi(self, city: str, country: str) -> Optional[Dict[str, Any]]:
        """
        使用 WeatherAPI.com 獲取天氣
        免費計劃：1,000,000 calls/month
        註冊：https://www.weatherapi.com/
        """
        if not self.api_key:
            logger.debug("WeatherAPI key not configured, skipping weather")
            return None

        url = "https://api.weatherapi.com/v1/current.json"
        params = {
            "key": self.api_key,
            "q": f"{city},{country}",
            "lang": self._get_lang_code("weatherapi"),
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_weatherapi(data)
                    else:
                        logger.warning(f"WeatherAPI error: {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.warning("WeatherAPI timeout")
            return None
        except Exception as e:
            logger.error(f"WeatherAPI error: {e}")
            return None

    def _parse_openweathermap(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """解析 OpenWeatherMap API 響應"""
        try:
            weather = data.get("weather", [{}])[0]
            main = data.get("main", {})
            wind = data.get("wind", {})

            return {
                "city": data.get("name", "未知"),
                "country": data.get("sys", {}).get("country", ""),
                "temperature": round(main.get("temp", 0)),
                "feels_like": round(main.get("feels_like", 0)),
                "temp_min": round(main.get("temp_min", 0)),
                "temp_max": round(main.get("temp_max", 0)),
                "humidity": main.get("humidity", 0),
                "pressure": main.get("pressure", 0),
                "description": weather.get("description", "未知"),
                "icon": weather.get("icon", ""),
                "wind_speed": round(wind.get("speed", 0), 1),
                "clouds": data.get("clouds", {}).get("all", 0),
                "provider": "OpenWeatherMap",
            }
        except Exception as e:
            logger.error(f"Error parsing OpenWeatherMap data: {e}")
            return {}

    def _parse_weatherapi(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """解析 WeatherAPI.com 響應"""
        try:
            location = data.get("location", {})
            current = data.get("current", {})
            condition = current.get("condition", {})

            # WeatherAPI uses celsius directly in metric
            return {
                "city": location.get("name", "未知"),
                "country": location.get("country", ""),
                "temperature": round(current.get("temp_c", 0)),
                "feels_like": round(current.get("feelslike_c", 0)),
                "temp_min": round(current.get("temp_c", 0)),  # WeatherAPI doesn't provide min/max in current
                "temp_max": round(current.get("temp_c", 0)),
                "humidity": current.get("humidity", 0),
                "pressure": current.get("pressure_mb", 0),
                "description": condition.get("text", "未知"),
                "icon": condition.get("icon", ""),
                "wind_speed": round(current.get("wind_kph", 0) / 3.6, 1),  # Convert km/h to m/s
                "clouds": current.get("cloud", 0),
                "provider": "WeatherAPI",
            }
        except Exception as e:
            logger.error(f"Error parsing WeatherAPI data: {e}")
            return {}

    def _get_lang_code(self, provider: str) -> str:
        """獲取 API 提供商的語言代碼"""
        lang_map = {
            "openweathermap": {
                "zh_tw": "zh_tw",
                "zh_cn": "zh_cn",
                "en": "en",
                "ja": "ja",
            },
            "weatherapi": {
                "zh_tw": "zh_tw",
                "zh_cn": "zh",
                "en": "en",
                "ja": "ja",
            },
        }

        provider_langs = lang_map.get(provider, {})
        return provider_langs.get(self.language, "zh_tw")

    def format_weather(self, weather_data: Dict[str, Any]) -> str:
        """
        格式化天氣數據為友好的文本

        Args:
            weather_data: 天氣數據字典

        Returns:
            格式化的天氣字符串
        """
        if not weather_data:
            return ""

        # 選擇天氣圖標
        icon = self._get_weather_emoji(weather_data.get("description", ""))

        city = weather_data.get("city", "")
        temp = weather_data.get("temperature", 0)
        feels_like = weather_data.get("feels_like", 0)
        description = weather_data.get("description", "")
        humidity = weather_data.get("humidity", 0)
        wind_speed = weather_data.get("wind_speed", 0)

        # 溫度單位
        unit = "°C" if self.units == "metric" else "°F"

        weather_text = f"{icon} **{city}** {description}\n"
        weather_text += f"🌡️ 溫度: {temp}{unit}"

        if abs(temp - feels_like) > 2:
            weather_text += f" (體感 {feels_like}{unit})"

        weather_text += f"\n💧 濕度: {humidity}%"

        if wind_speed > 5:  # Only show wind if significant
            weather_text += f" | 💨 風速: {wind_speed}m/s"

        return weather_text

    def _get_weather_emoji(self, description: str) -> str:
        """根據天氣描述返回合適的 emoji"""
        description = description.lower()

        if any(word in description for word in ["晴", "clear", "sunny"]):
            return "☀️"
        elif any(word in description for word in ["雲", "cloud", "overcast"]):
            return "☁️"
        elif any(word in description for word in ["雨", "rain", "drizzle"]):
            return "🌧️"
        elif any(word in description for word in ["雪", "snow"]):
            return "❄️"
        elif any(word in description for word in ["雷", "thunder", "storm"]):
            return "⛈️"
        elif any(word in description for word in ["霧", "fog", "mist", "haze"]):
            return "🌫️"
        else:
            return "🌤️"

    def get_weather_advice(self, weather_data: Dict[str, Any]) -> str:
        """
        根據天氣提供建議

        Args:
            weather_data: 天氣數據

        Returns:
            天氣建議文本
        """
        if not weather_data:
            return ""

        advices = []
        temp = weather_data.get("temperature", 20)
        description = weather_data.get("description", "").lower()
        humidity = weather_data.get("humidity", 50)
        wind_speed = weather_data.get("wind_speed", 0)

        # 溫度建議
        if temp < 10:
            advices.append("🧥 天氣較冷，記得多穿點衣服")
        elif temp > 30:
            advices.append("🥵 天氣炎熱，注意防曬和補水")
        elif temp > 25:
            advices.append("😎 天氣溫暖，適合外出活動")

        # 天氣狀況建議
        if any(word in description for word in ["雨", "rain"]):
            advices.append("☔ 記得帶傘")
        elif any(word in description for word in ["雪", "snow"]):
            advices.append("⛄ 路面可能濕滑，注意安全")
        elif any(word in description for word in ["霧", "fog", "haze"]):
            advices.append("😷 空氣品質可能不佳，建議戴口罩")

        # 濕度建議
        if humidity > 80:
            advices.append("💧 濕度較高，注意防潮")
        elif humidity < 30:
            advices.append("💦 空氣乾燥，多喝水")

        # 風速建議
        if wind_speed > 10:
            advices.append("💨 風速較大，外出小心")

        return "\n".join(advices) if advices else ""


# 全局天氣服務實例
_weather_service: Optional[WeatherService] = None


def get_weather_service() -> WeatherService:
    """獲取天氣服務單例"""
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service
