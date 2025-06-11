from dataclasses import dataclass
from typing import Optional
import requests
from datetime import datetime
from dotenv import load_dotenv
import os
import sqlite3
from enum import Enum
import logging

logging.basicConfig(
    level=logging.DEBUG,  # Set the minimum level to log
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='aqi.log',  # Log to a file
    filemode='a'
)

class AQILevel(Enum):
    GOOD = (0, 50, "Good")
    MODERATE = (51, 100, "Moderate")
    UNHEALTHY_SENSITIVE = (101, 150, "Unhealthy for Sensitive Groups")
    UNHEALTHY = (151, 200, "Unhealthy")
    VERY_UNHEALTHY = (201, 300, "Very Unhealthy")
    HAZARDOUS = (301, 500, "Hazardous")

    @classmethod
    def get_level(cls, aqi: int) -> 'AQILevel':
        for level in cls:
            if level.value[0] <= aqi <= level.value[1]:
                return level
        return cls.HAZARDOUS

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

def adapt_datetime(val: datetime) -> str:
    """将datetime转换为SQLite存储格式"""
    return val.isoformat()

def convert_datetime(val: bytes) -> datetime:
    """从SQLite格式转换回datetime"""
    return datetime.fromisoformat(val.decode())

def init_db():
    """初始化SQLite数据库"""
    # 注册datetime适配器
    sqlite3.register_adapter(datetime, adapt_datetime)
    sqlite3.register_converter("datetime", convert_datetime)
    
    conn = sqlite3.connect('aqi_history.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS aqi_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp datetime,
            aqi INTEGER,
            level TEXT,
            station TEXT,
            dominentpol TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_last_record() -> Optional[tuple]:
    """获取最后一条记录"""
    conn = sqlite3.connect('aqi_history.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('SELECT aqi, level FROM aqi_records ORDER BY timestamp DESC LIMIT 1')
    result = c.fetchone()
    conn.close()
    return result

def notify_level_change(data: AQIResponse, old_level: str, new_level: str):
    logging.info(f"监测到AQI跳变：{old_level} -> {new_level}")

    message = f"当前AQI: {data.aqi} {new_level}, 主要污染物: {data.dominentpol}"
    logging.info(f"准备发送邮件通知：{message}")

    # TODO: send_email(message)
    print( message )

def store_aqi(data: AQIResponse):
    """存储AQI数据并检查等级变化"""
    level = AQILevel.get_level(data.aqi)
    
    # 获取上一条记录
    last_record = get_last_record()
    
    # 存储新记录
    conn = sqlite3.connect('aqi_history.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('''
        INSERT INTO aqi_records (timestamp, aqi, level, station, dominentpol)
        VALUES (?, ?, ?, ?, ?)
    ''', (data.time, data.aqi, level.name, data.station, data.dominentpol))
    conn.commit()
    conn.close()
    
    if last_record and last_record[1] != level.name:
        notify_level_change(data, last_record[1], level.name)
    else:
        logging.info(f"没有监测到跳变，当前AQI: {data.aqi} {level.name}")

def get_aqi(token: str) -> AQIResponse:
    """获取浦东惠南的AQI数据"""
    url = f"https://api.waqi.info/feed/shanghai/pudonghuinan/?token={token}"
    
    response = requests.get(url)
    data = response.json()
    
    if data['status'] != 'ok':
        logging.error(f"API返回错误: {data.get('data')}")
        raise ValueError(f"API返回错误: {data.get('data')}")
        
    return AQIResponse.from_response(data['data'])

# 使用示例
if __name__ == "__main__":
    logging.info("\n\n====")

    load_dotenv()
    TOKEN = os.getenv("AQICN_TOKEN")
    
    # 确保数据库已初始化
    init_db()
    
    try:
        result = get_aqi(TOKEN)
        # 存储数据并检查等级变化
        store_aqi(result)
        
        # 打印当前状态
        level = AQILevel.get_level(result.aqi)
        print(f"\n浦东惠南AQI:")
        print(f"站点: {result.station}")
        print(f"AQI: {result.aqi}")
        print(f"等级: {level.name} ({level.value[2]})")
        print(f"主要污染物: {result.dominentpol}")
        print(f"更新时间: {result.time}")

        logging.info(f"成功获取浦东惠南AQI: {result.aqi}")
        logging.info(f"主要污染物: {result.dominentpol}")

    except (requests.RequestException, ValueError) as e:
        print(f"错误: {str(e)}") 
        logging.error(f"错误: {str(e)}")