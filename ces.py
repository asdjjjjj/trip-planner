import requests

# ========== 配置 ==========
AMAP_KEY = "YOUR_AMAP_KEY"  # 替换为你在开放平台创建的【Web服务】类型 key
city = "北京"
address = "天安门广场"
# ==========================

def geocode_test():
    """地理编码：地址转经纬度"""
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        "address": address,
        "city": city,
        "key": AMAP_KEY
    }
    resp = requests.get(url, params=params)
    print("【地理编码结果】")
    print(resp.json())


def ip_location_test():
    """IP定位测试"""
    url = "https://restapi.amap.com/v3/ip"
    params = {
        "ip": "223.5.5.5",
        "key": AMAP_KEY
    }
    resp = requests.get(url, params=params)
    print("\n【IP定位结果】")
    print(resp.json())


if __name__ == "__main__":
    geocode_test()
    ip_location_test()
