"""高德地图 Web 服务封装（直接调用高德 REST API，不依赖 MCP 工具）"""

from typing import Dict, List, Optional

import requests

from ..config import get_settings
from ..models.schemas import Location, POIInfo, WeatherInfo

# 高德地图 Web 服务基础地址
AMAP_BASE_URL = "https://restapi.amap.com"


class AmapService:
    """高德地图服务封装类"""

    def __init__(self):
        """初始化服务"""
        settings = get_settings()
        if not settings.amap_api_key:
            raise ValueError("高德地图 API Key 未配置，请在 .env 中设置 AMAP_API_KEY")
        self.api_key = settings.amap_api_key

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------
    def _get(self, path: str, params: Dict[str, str]) -> dict:
        """发起高德地图 GET 请求并返回 JSON"""
        payload = {**params, "key": self.api_key}
        resp = requests.get(f"{AMAP_BASE_URL}{path}", params=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "1":
            raise ValueError(f"高德地图接口返回错误：{data.get('info')}")
        return data

    @staticmethod
    def _parse_location(location: Optional[str]) -> Optional[Location]:
        """将高德返回的「经度,纬度」字符串解析为 Location 对象"""
        if not location:
            return None
        try:
            lon, lat = location.split(",")
            return Location(longitude=float(lon), latitude=float(lat))
        except (ValueError, AttributeError):
            return None

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def search_poi(self, keywords: str, city: str, citylimit: bool = True) -> List[POIInfo]:
        """搜索兴趣点（POI）"""
        data = self._get(
            "/v3/place/text",
            {
                "keywords": keywords,
                "city": city,
                "citylimit": str(citylimit).lower(),
                "offset": "20",
            },
        )

        pois: List[POIInfo] = []
        for item in data.get("pois") or []:
            pois.append(
                POIInfo(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    type=item.get("type", ""),
                    address=item.get("address", ""),
                    location=self._parse_location(item.get("location"))
                    or Location(longitude=0, latitude=0),
                    tel=item.get("tel") or None,
                )
            )
        return pois

    def get_weather(self, city: str) -> List[WeatherInfo]:
        """查询城市天气（先地理编码获取城市编码，再查询天气）"""
        # 通过地理编码接口获取城市的 adcode
        geo = self._get("/v3/geocode/geo", {"address": city})
        geocodes = geo.get("geocodes") or []
        if not geocodes:
            return []
        adcode = geocodes[0].get("adcode", "")

        data = self._get("/v3/weather/weatherInfo", {"city": adcode, "extensions": "all"})
        result: List[WeatherInfo] = []
        for item in data.get("forecasts") or []:
            for cast in item.get("casts") or []:
                result.append(
                    WeatherInfo(
                        date=cast.get("date", ""),
                        day_weather=cast.get("dayweather", ""),
                        night_weather=cast.get("nightweather", ""),
                        day_temp=cast.get("daytemp", 0),
                        night_temp=cast.get("nighttemp", 0),
                        wind_direction=cast.get("daywind", ""),
                        wind_power=cast.get("daypower", ""),
                    )
                )
        return result

    def plan_route(
        self,
        origin_address: str,
        destination_address: str,
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
        route_type: str = "walking",
    ) -> Dict:
        """规划两点之间的路线"""
        tool_map = {
            "walking": "/v3/direction/walking",
            "driving": "/v3/direction/driving",
            "transit": "/v3/direction/transit/integrated",
        }
        path = tool_map.get(route_type, "/v3/direction/walking")

        params = {
            "origin": origin_address,
            "destination": destination_address,
        }
        if origin_city:
            params["city"] = origin_city
        if destination_city and route_type == "transit":
            params["cityd"] = destination_city

        data = self._get(path, params)
        paths = data.get("route", {}).get("paths") or []
        if not paths:
            return {}

        first = paths[0]
        distance = float(first.get("distance", 0))
        duration = int(first.get("duration", 0))
        return {
            "distance": distance,
            "duration": duration,
            "route_type": route_type,
            "description": f"路线距离 {distance:.0f} 米，预计耗时 {max(1, duration // 60)} 分钟",
        }

    def geocode(self, address: str, city: Optional[str] = None) -> Optional[Location]:
        """地理编码（地址转经纬度）"""
        params = {"address": address}
        if city:
            params["city"] = city

        data = self._get("/v3/geocode/geo", params)
        geocodes = data.get("geocodes") or []
        if not geocodes:
            return None
        return self._parse_location(geocodes[0].get("location"))

    def get_poi_detail(self, poi_id: str) -> Dict:
        """获取 POI 详情"""
        data = self._get("/v3/place/detail", {"id": poi_id})
        pois = data.get("pois") or []
        return pois[0] if pois else {"raw": "未找到该 POI"}


# 全局服务实例
_amap_service = None


def get_amap_service() -> AmapService:
    """获取高德地图服务实例（单例模式）"""
    global _amap_service

    if _amap_service is None:
        _amap_service = AmapService()

    return _amap_service
