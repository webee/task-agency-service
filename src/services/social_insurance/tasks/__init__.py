import datetime

dic={'03':[{'1':'201606','2':'ceshi'}]}
da={'04':[{'1':'201606','2':'ceshi'}]}
for y in range(-1,4-1):
    statatime ='201603'
    nowtime = datetime.date(int(statatime[:4])+(int(statatime[-2:]) + y)//12,(int(statatime[-2:]) + y)%12+1,1).strftime('%Y-%m-%d')
    strtimemonth=nowtime[:7].replace('-','')
    dic['03'][0]['1']=strtimemonth
    print(dic)
    print(da)

