"""天气工具：优先调用 OpenWeatherMap API，无 Key 时使用模拟结果。"""

from __future__ import annotations

import os
from typing import Any

import requests

from tools.base_tool import BaseTool


class WeatherTool(BaseTool):
    """查询城市天气信息。"""

    name = "weather"
    description = "查询指定城市天气"
    parameters = {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名，如 Beijing"},
        },
        "required": ["city"],
    }

    def execute(self, **kwargs: Any) -> str:
        """执行天气查询并返回摘要信息。"""
        city = kwargs.get("city", "").strip()
        if not city:
            return "天气查询失败：city 不能为空。"

        api_key = os.getenv("WEATHER_API_KEY")
        if not api_key:
            # 无密钥时提供固定格式模拟输出。
            return f"[模拟天气结果] {city}：晴，约 26°C。请配置 WEATHER_API_KEY 以获取实时天气。"

        try:
            response = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": api_key, "units": "metric", "lang": "zh_cn"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            weather = data.get("weather", [{}])[0].get("description", "未知")
            temp = data.get("main", {}).get("temp", "未知")
            humidity = data.get("main", {}).get("humidity", "未知")
            return f"{city} 当前天气：{weather}，温度 {temp}°C，湿度 {humidity}%。"
        except Exception as exc:  # noqa: BLE001 - 需要兜底异常避免主流程崩溃
            return f"天气调用失败：{exc}"
