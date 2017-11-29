import requests

def get_proxy_ip():
    # 这里填写无忧代理IP提供的API订单号（请到用户中心获取）
    order = "b47c46d42da0fe61e4bc0b139851ae2a"
    # 获取IP的API接口
    apiUrl = "http://api.ip.data5u.com/dynamic/get.html?order=" + order
    res = requests.get(apiUrl)
    # 按照\n分割获取到的IP
    ip = res.text.replace("\n", "")
    return ip