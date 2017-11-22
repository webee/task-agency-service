# -*- coding: UTF-8 -*-

'''
无忧代理IP Created on 2017年08月21日
描述：本DEMO演示了使用爬虫（动态）代理IP请求网页的过程，代码使用了多线程
逻辑：每隔5秒从API接口获取IP，对于每一个IP开启一个线程去抓取网页源码
@author: www.data5u.com
'''
import random
import time

import requests

ips = []


# 获取代理IP的线程类
class GetIpThread(object):
    def getip(self):
        # 这里填写无忧代理IP提供的API订单号（请到用户中心获取）
        order = "b47c46d42da0fe61e4bc0b139851ae2a"
        # 获取IP的API接口
        apiUrl = "http://api.ip.data5u.com/dynamic/get.html?order=" + order
        # 要抓取的目标网站地址
        targetUrl = "http://www.12333sh.gov.cn/sbsjb/wzb/Bmblist12.jsp"
        res = requests.get(apiUrl)
        # 按照\n分割获取到的IP
        ips = res.text.replace("\n", "")
        return ips
