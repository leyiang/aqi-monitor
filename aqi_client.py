from dataclasses import dataclass
import requests
from datetime import datetime
from dotenv import load_dotenv
import os

@dataclass
class AQIResponse:
    aqi: int
    time: datetime
    station: str
    dominentpol: str
    
    @classmethod
    def from_response(cls, data: dict) -> 'AQIResponse':
        return cls(
            aqi=data['aqi'],
            time=datetime.fromisoformat(data['time']['iso']),
            station=data['city']['name'],
            dominentpol=data['dominentpol']
        )

def get_aqi(token: str) -> AQIResponse:
    """获取浦东惠南的AQI数据"""
    url = f"https://api.waqi.info/feed/shanghai/pudonghuinan/?token={token}"
    
    response = requests.get(url)
    data = response.json()
    
    if data['status'] != 'ok':
        raise ValueError(f"API返回错误: {data.get('data')}")
        
    return AQIResponse.from_response(data['data'])

# 使用示例
if __name__ == "__main__":
    # 替换为你的API token
    load_dotenv()
    TOKEN = os.getenv("AQICN_TOKEN")
    
    try:
        result = get_aqi(TOKEN)

        print(f"\n浦东惠南AQI:")
        print(f"站点: {result.station}")
        print(f"AQI: {result.aqi}")
        print(f"主要污染物: {result.dominentpol}")
        print(f"更新时间: {result.time}")
        
    except (requests.RequestException, ValueError) as e:
        print(f"错误: {str(e)}") 