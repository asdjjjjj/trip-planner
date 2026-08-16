"""智能旅行规划器（基于 LangChain）"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from langchain_core.messages import AIMessage

from ..config import get_settings
from ..models.schemas import (
    Attraction,
    DayPlan,
    Hotel,
    Location,
    Meal,
    TripPlan,
    TripRequest,
    WeatherInfo,
)
from ..services.amap_service import get_amap_service
from ..services.llm_service import get_llm

logger = logging.getLogger(__name__)

# 行程规划系统提示词
PLANNER_SYSTEM_PROMPT = """你是行程规划专家。请根据提供的城市、景点、天气和酒店信息，生成详细的旅行计划。

要求：
1. 严格以 JSON 格式返回，不要输出 Markdown 代码块或多余文字；
2. JSON 必须包含以下字段：
   - city：城市名称
   - start_date / end_date：开始/结束日期（YYYY-MM-DD）
   - days：每日行程数组，每项包含 date、day_index、description、transportation、
     accommodation、hotel（name/address/location/price_range/rating/distance/type/estimated_cost）、
     attractions（name/address/location/visit_duration/description/category/ticket_price）、
     meals（breakfast/lunch/dinner 三项，含 type/name/description/estimated_cost）
   - weather_info：每天天气数组（date/day_weather/night_weather/day_temp/night_temp/wind_direction/wind_power）
   - overall_suggestions：总体建议
   - budget：预算汇总（total_attractions/total_hotels/total_meals/total_transportation/total）
3. 每天安排 2-3 个景点，考虑景点之间的距离和游览时间；
4. 每天必须包含早中晚三餐；
5. 温度必须是纯数字（不要带 °C 等单位）；
6. 提供实用的旅行建议。"""


class TripPlanner:
    """旅行规划器：检索景点/天气/酒店数据，并由大模型生成行程计划"""

    def __init__(self):
        """初始化旅行规划器"""
        self.settings = get_settings()
        self.llm = get_llm()
        self.amap = get_amap_service()
        print("旅行规划器初始化成功")

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    def plan_trip(self, request: TripRequest) -> TripPlan:
        """生成旅行计划"""
        try:
            print(f"开始规划旅行：{request.city}，{request.travel_days} 天")

            # 步骤1：搜索景点（取第一个偏好作为关键词）
            print("步骤1：搜索景点...")
            keyword = (request.preferences or ["景点"])[0]
            attractions = self.amap.search_poi(keyword, request.city)
            print(f"搜索到 {len(attractions)} 个景点")

            # 步骤2：查询天气
            print("步骤2：查询天气...")
            weather = self.amap.get_weather(request.city)
            print(f"获取到 {len(weather)} 天天气")

            # 步骤3：搜索酒店
            print("步骤3：搜索酒店...")
            hotels = self.amap.search_poi("酒店", request.city)
            print(f"搜索到 {len(hotels)} 个酒店")

            # 步骤4：调用大模型生成行程
            print("步骤4：生成行程计划...")
            prompt = self._build_planner_prompt(request, attractions, weather, hotels)
            response = self._invoke_llm(prompt)
            trip_plan = self._parse_response(response, request)

            print("旅行计划生成完成")
            return trip_plan

        except Exception as exc:
            logger.exception("生成旅行计划失败", exc_info=exc)
            print(f"生成旅行计划失败，使用备用方案：{exc}")
            return self._create_fallback_plan(request)

    # ------------------------------------------------------------------
    # 提示词构建
    # ------------------------------------------------------------------
    def _build_planner_prompt(
        self,
        request: TripRequest,
        attractions,
        weather: List[WeatherInfo],
        hotels,
    ) -> str:
        """构建行程规划提示词"""
        attractions_text = self._format_attractions(attractions)
        weather_text = self._format_weather(weather)
        hotels_text = self._format_hotels(hotels)

        prompt = f"""请根据以下信息生成{request.city}的{request.travel_days}天旅行计划：

**基本信息：**
- 城市：{request.city}
- 日期：{request.start_date} 至 {request.end_date}
- 天数：{request.travel_days}天
- 交通方式：{request.transportation}
- 住宿偏好：{request.accommodation}
- 旅行偏好：{', '.join(request.preferences) if request.preferences else '无'}

**景点信息：**
{attractions_text}

**天气信息：**
{weather_text}

**酒店信息：**
{hotels_text}

**要求：**
1. 每天安排 2-3 个景点，优先选择上面给出的真实景点；
2. 每天必须包含早中晚三餐；
3. 每天推荐一个具体的酒店（从酒店信息中选择）；
4. 考虑景点之间的距离和交通方式；
5. 返回完整的 JSON 格式数据；
6. 景点的经纬度坐标要真实准确。"""

        if request.free_text_input:
            prompt += f"\n\n**额外要求：** {request.free_text_input}"

        return prompt

    @staticmethod
    def _format_attractions(attractions) -> str:
        """格式化景点信息"""
        lines = []
        for item in attractions[:10]:
            loc = f"{item.location.longitude},{item.location.latitude}"
            lines.append(f"- {item.name}（{item.type}）：{item.address}，坐标 {loc}")
        return "\n".join(lines) or "暂无景点数据"

    @staticmethod
    def _format_weather(weather: List[WeatherInfo]) -> str:
        """格式化天气信息"""
        lines = [
            f"- {w.date}：白天{w.day_weather} {w.day_temp}°C，夜间{w.night_weather} {w.night_temp}°C，"
            f"{w.wind_direction} {w.wind_power}"
            for w in weather
        ]
        return "\n".join(lines) or "暂无天气数据"

    @staticmethod
    def _format_hotels(hotels) -> str:
        """格式化酒店信息"""
        lines = [f"- {item.name}（{item.type}）：{item.address}" for item in hotels[:10]]
        return "\n".join(lines) or "暂无酒店数据"

    # ------------------------------------------------------------------
    # 大模型调用与解析
    # ------------------------------------------------------------------
    def _invoke_llm(self, prompt: str) -> str:
        """调用大模型生成 JSON 行程（json_object 模式，失败时回退普通输出）"""
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            bound = self.llm.bind(response_format={"type": "json_object"})
            response = bound.invoke(messages)
        except Exception as exc:
            logger.warning("JSON 模式不可用（%s），回退到普通输出", exc)
            response = self.llm.invoke(messages)

        if isinstance(response, AIMessage):
            return str(response.content or "")
        return str(response)

    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        """解析大模型返回的 JSON 行程计划"""
        try:
            # 优先提取 ```json 代码块，其次直接查找 JSON 对象
            json_str = response
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "{" in response and "}" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]

            data = json.loads(json_str)
            data = self._normalize_plan_data(data)
            return TripPlan(**data)

        except Exception as exc:
            logger.warning("解析行程响应失败：%s", exc)
            print(f"解析响应失败，使用备用方案：{exc}")
            return self._create_fallback_plan(request)

    @staticmethod
    def _normalize_plan_data(data: dict) -> dict:
        """将大模型输出的 JSON 归一化为 TripPlan 兼容格式

        大模型返回的字段格式往往不够规范（如坐标是字符串、时长带单位、餐饮是字典），
        这里做容错转换，避免因格式问题触发备用方案。
        """
        if not isinstance(data, dict):
            return data

        def to_location(value):
            """兼容 {'longitude':..,'latitude':..} 与 '经度,纬度' 两种格式"""
            if isinstance(value, dict):
                return value
            if isinstance(value, str) and "," in value:
                try:
                    lon, lat = value.split(",")
                    return {"longitude": float(lon.strip()), "latitude": float(lat.strip())}
                except ValueError:
                    pass
            return None

        def to_minutes(value):
            """将 '4小时'、'1.5小时'、'90分钟' 或纯数字转换为分钟整数"""
            if isinstance(value, (int, float)):
                return int(value)
            text = str(value)
            if "小时" in text:
                try:
                    return int(float(text.replace("小时", "").strip()) * 60)
                except ValueError:
                    pass
            if "分钟" in text:
                try:
                    return int(float(text.replace("分钟", "").strip()))
                except ValueError:
                    pass
            try:
                return int(float(text))
            except ValueError:
                return 120

        def to_int(value):
            """将字符串数字转换为整数"""
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return 0

        # 归一化每天的行程数据
        for day in data.get("days") or []:
            if not isinstance(day, dict):
                continue

            # 景点
            for attr in day.get("attractions") or []:
                if not isinstance(attr, dict):
                    continue
                loc = to_location(attr.get("location"))
                if loc:
                    attr["location"] = loc
                elif attr.get("location") is not None:
                    # 无法解析的坐标，置为占位值以保证校验通过
                    attr["location"] = {"longitude": 0, "latitude": 0}
                attr["visit_duration"] = to_minutes(attr.get("visit_duration"))
                if isinstance(attr.get("ticket_price"), str):
                    attr["ticket_price"] = to_int(attr["ticket_price"])

            # 酒店
            hotel = day.get("hotel")
            if isinstance(hotel, dict):
                loc = to_location(hotel.get("location"))
                if loc:
                    hotel["location"] = loc
                elif hotel.get("location") is not None:
                    hotel["location"] = None
                if isinstance(hotel.get("rating"), (int, float)):
                    hotel["rating"] = str(hotel["rating"])
                if isinstance(hotel.get("estimated_cost"), str):
                    hotel["estimated_cost"] = to_int(hotel["estimated_cost"])

            # 餐饮：字典结构（按类型分组）转列表结构
            meals = day.get("meals")
            if isinstance(meals, dict):
                meal_list = []
                for meal_type, meal in meals.items():
                    if isinstance(meal, dict):
                        meal_list.append({**meal, "type": meal_type})
                    else:
                        meal_list.append({"type": meal_type, "name": str(meal)})
                day["meals"] = meal_list
            elif isinstance(meals, list):
                for meal in meals:
                    if isinstance(meal, dict) and isinstance(meal.get("estimated_cost"), str):
                        meal["estimated_cost"] = to_int(meal["estimated_cost"])

        # 天气温度转数字
        for item in data.get("weather_info") or []:
            if not isinstance(item, dict):
                continue
            for key in ("day_temp", "night_temp"):
                value = item.get(key)
                if isinstance(value, str):
                    cleaned = value.replace("°C", "").replace("℃", "").replace("°", "").strip()
                    try:
                        item[key] = int(float(cleaned))
                    except ValueError:
                        item[key] = 0

        # 预算转整数
        budget = data.get("budget")
        if isinstance(budget, dict):
            for key in (
                "total_attractions",
                "total_hotels",
                "total_meals",
                "total_transportation",
                "total",
            ):
                if key in budget:
                    budget[key] = to_int(budget[key])

        return data

    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        """创建备用计划（当大模型或数据检索失败时）"""
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")

        days: List[DayPlan] = []
        for i in range(request.travel_days):
            current_date = start_date + timedelta(days=i)
            days.append(
                DayPlan(
                    date=current_date.strftime("%Y-%m-%d"),
                    day_index=i,
                    description=f"第{i + 1}天行程",
                    transportation=request.transportation,
                    accommodation=request.accommodation,
                    attractions=[
                        Attraction(
                            name=f"{request.city}景点{j + 1}",
                            address=f"{request.city}市",
                            location=Location(
                                longitude=116.4 + i * 0.01 + j * 0.005,
                                latitude=39.9 + i * 0.01 + j * 0.005,
                            ),
                            visit_duration=120,
                            description=f"这是{request.city}的著名景点",
                            category="景点",
                        )
                        for j in range(2)
                    ],
                    meals=[
                        Meal(type="breakfast", name=f"第{i + 1}天早餐", description="当地特色早餐"),
                        Meal(type="lunch", name=f"第{i + 1}天午餐", description="午餐推荐"),
                        Meal(type="dinner", name=f"第{i + 1}天晚餐", description="晚餐推荐"),
                    ],
                )
            )

        return TripPlan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=days,
            weather_info=[],
            overall_suggestions=f"这是为您规划的{request.city}{request.travel_days}日游行程，建议提前查看各景点的开放时间。",
        )


# 全局旅行规划器实例
_trip_planner = None


def get_trip_planner() -> TripPlanner:
    """获取旅行规划器实例（单例模式）"""
    global _trip_planner

    if _trip_planner is None:
        _trip_planner = TripPlanner()

    return _trip_planner
