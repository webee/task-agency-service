
import time
import re
import requests
from urllib import parse
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError
from services.commons import AbsFetchTask
from  services.errors import InvalidParamsError

MAIN_URL = 'http://www.aygjj.com/gjjcx/zfbzgl/zfbzsq/main_menu.jsp'
LOGIN_URL = 'http://www.aygjj.com/gjjcx/zfbzgl/zfbzsq/login_hidden.jsp'
VC_URL = 'http://www.aygjj.com/gjjcx/zfbzgl/zfbzsq/image.jsp'
GJJMX_URL='http://www.aygjj.com/gjjcx/zfbzgl/gjjmxcx/gjjmx_cx.jsp'
GJJ_URL='http://www.aygjj.com/gjjcx/zfbzgl/zfbzsq/gjjmx_cxtwo.jsp'


class Task(AbsFetchTask):
    task_info = dict(
        city_name="安阳",
        help="""<li>初始密码为111111。</li>
                <li>如身份证最后一位是“X”时，请输入大写X。</li>""",
        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'
        }

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_name, self._unit_login)


    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '身份证号' in params, '缺少身份证号'
        assert '职工姓名' in params, '缺少职工姓名'
        assert '密码' in params,'缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check
        身份证号 = params['身份证号']
        职工姓名= params['职工姓名']
        密码 = params['密码']

        if len(身份证号) == 0:
            raise InvalidParamsError('身份证号为空，请输入身份证号')
        elif len(身份证号) < 15:
            raise InvalidParamsError('身份证号不正确，请重新输入')

        if len(职工姓名) == 0:
            raise InvalidParamsError('职工姓名为空，请输入职工姓名')
        elif len(职工姓名) < 2:
            raise InvalidParamsError('职工姓名不正确，请重新输入')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')
    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '身份证号' not in params:
                params['身份证号'] = meta.get('身份证号')
            if '职工姓名' not in params:
                params['职工姓名'] = meta.get('职工姓名')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '身份证号' and '身份证号' in meta:
                continue
            elif pr['key'] == '职工姓名' and '职工姓名' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            res.append(pr)
        return res

    def _unit_login(self, params=None):
        err_msg = None
        params
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params['身份证号']
                account_num = params['职工姓名']
                password=params['密码']
                vc = params['vc']
                data = dict(
                    cxydmc='当前年度',
                    zgzh='',
                    zgxm1=account_num,
                    sfzh=id_num,
                    password=password,
                    yzm=vc
                )
                resp = self.s.post(LOGIN_URL,data=parse.urlencode(data,encoding='gbk'),headers={'Content-Type':'application/x-www-form-urlencoded'},timeout=10)

                soup = BeautifulSoup(resp.content, 'html.parser')

                return_message =soup.find('head') #soup.find('input', {'name': 'zgzh'})["value"]
                if len(return_message.text)>3:
                    return_message=return_message.text.split(';')[0].split('"')[1]
                    raise InvalidParamsError(return_message)
                else:
                    print("登录成功！")
                    self.zgzh=soup.find('input', {'name': 'zgzh'})["value"]
                    self.sfzh=soup.find('input', {'name': 'sfzh'})["value"]
                    self.zgxm=soup.find('input', {'name': 'zgxm'})["value"]
                    self.dwbm = soup.find('input', {'name': 'dwbm'})["value"]
                    self.cxyd=soup.find('input', {'name': 'cxyd'})["value"]
                    data2 = dict(zgzh=self.zgzh,
                                 sfzh=self.sfzh,
                                 zgxm=self.zgxm,
                                 dwbm=self.dwbm,cxyd=self.cxyd)

                    resp2 = self.s.post(MAIN_URL, data=parse.urlencode(data2, encoding='gbk'),
                                  headers={'Content-Type': 'application/x-www-form-urlencoded'},timeout=10)
                    soup2 = BeautifulSoup(resp2.content, 'html.parser')
                    self.html = str(resp2.content, 'gbk')

                self.result_key =id_num
                self.result_meta['身份证号'] = id_num
                self.result_meta['职工姓名'] = account_num
                self.result_meta['密码'] = password

                self.result_identity['task_name'] = '安阳'
                self.result_identity['target_id'] = id_num
                self.result_identity['target_name'] = account_num

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input'),
            dict(key='职工姓名', name='职工姓名', cls='input'),
            dict(key='密码',name='密码',cls='input:password'),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            data = self.result_data
            # 基本信息
            resp = self.html
            soup = BeautifulSoup(resp, 'html.parser')
            table_text = soup.select('table.1')
            rows = table_text[0].find_all('tr')
            data['baseInfo'] = {
                '城市名称': '安阳',
                '城市编号': '410500',
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '证件类型':'身份证'
            }
            for row in rows:
                cell = [i.text for i in row.find_all('td')]
                data['baseInfo'].setdefault(cell[0].replace('职工姓名','姓名').replace('职工账号','个人账号').replace('所在单位','单位名称').replace('月缴基数','缴存基数').replace('账户状态','帐户状态').replace('上年余额','上年结转余额').replace('本年缴交','当年缴存金额').replace(' ',''),cell[1].replace('\xa0',''))
                data['baseInfo'].setdefault(cell[2].replace('身份证号','证件号').replace(' ','').replace('本年支取','当年提取金额').replace('月缴金额','月应缴额').replace('账户余额','当前余额'), cell[3].replace('\xa0',''))
            if '正常' in data['baseInfo']['帐户状态']:
                self.result_identity['status'] ='缴存'
            else:
                self.result_identity['status'] ='封存'

            resp = self.s.post(GJJMX_URL,data = parse.urlencode(dict(zgzh=self.zgzh,sfzh=self.sfzh,zgxm=self.zgxm,dwbm=self.dwbm,cxyd=self.cxyd), encoding='gbk'),headers={'Content-Type': 'application/x-www-form-urlencoded','Accept-Language':'zh-CN,zh;q=0.8'},timeout=5)
            soup = BeautifulSoup(resp.content, 'html.parser')
            data['detail'] = {}
            data['detail']['data'] = {}
            selectyear = []
            years = ''
            months = ''
            hjtype = 0
            hjcs = 0
            hjje = ''
            hjrq = ''
            for option in soup.findAll('option'):
                selectyear.append(option.getText())
            selectyear.append('当前年度')
            for y in range(1,len(selectyear)):
                cxydone=selectyear[y]
                cxydtwo1=''
                if y==0:
                    cxydtwo1=selectyear[y]
                else:
                    cxydtwo1 = selectyear[y-1]
                data1={'zgzh':self.zgzh,
                           'cxydtwo':cxydone,
                           'cxydtwo':cxydtwo1,
                           'sfzh':self.sfzh,
                           'zgxm':self.zgxm,
                           'dwbm':self.dwbm,
                           'cxyd':cxydtwo1}
                resp = self.s.post(GJJ_URL, data=parse.urlencode(data1, encoding='gbk'),
                                  headers={'Content-Type': 'application/x-www-form-urlencoded','Accept-Language':'zh-CN,zh;q=0.8'},timeout=5)
                soup = BeautifulSoup(resp.content, 'html.parser')
                tab=soup.select('table')[16]
                tabtitle=tab.findAll('tr')[0]
                tabcontent=tab.select('.jtpsoft')
                titkeys = '时间,类型,支出,收入,借贷方向,余额'
                # for td in tabtitle.findAll('td'):
                #     if len(titkeys) < 1:
                #         titkeys = td.getText()
                #     else:
                #         titkeys = titkeys + ',' + td.getText()
                w=0   #获取本页倒数第二条
                for tr in range(0,len(tabcontent)):
                    dic = {}
                    i = 0
                    monthkeys = ''
                    arr=[]
                    w=w+1
                    if w==len(tabcontent)-1:
                        w=-1
                    for td in tabcontent[tr].findAll('td'):
                        dic.setdefault(titkeys.split(',')[i], td.getText())
                        i = i + 1
                        if i == 1:
                            monthkeys = td.getText()
                        if i == 2:
                            hjny=''
                            lx=td.getText()
                            if '汇缴' in td.getText():
                                hjcs=hjcs+1
                                hjny=td.getText().replace('汇缴','').replace('年','').replace('月','')
                                lx='汇缴'
                            if hjny and hjtype==0 and w==-1:
                                hjtype=1
                                hjrq=hjny
                            dic.setdefault('汇缴年月', hjny)
                            dic['类型']=lx
                        if i==4:
                            if hjtype==1 and w==-1:
                                hjtype=2
                                hjje=td.getText()
                        if i == 6:
                            dic['单位名称']= ''
                            if years==''or years!=monthkeys[:4]:
                                years=monthkeys[:4]
                                if years not in data['detail']['data'].keys():
                                    data['detail']['data'][years]={}
                                if months==monthkeys[5:7]:
                                    if months not in data['detail']['data'][years].keys():
                                        data['detail']['data'][years][months] = {}
                            if months=='' or months!=monthkeys[5:7]:
                                months=monthkeys[5:7]
                                if months not in data['detail']['data'][years].keys():
                                    data['detail']['data'][years][months] = {}
                            if len(data['detail']['data'][years][months])>0:
                                arr=data['detail']['data'][years][months]
                            arr.append(dic)
                            data['detail']['data'][years][months]=arr
            data['baseInfo']['最近汇缴日期'] = hjrq
            data['baseInfo']['最近汇缴金额'] = hjje
            data['baseInfo']['累计汇缴次数'] = hjcs
            data['companyList']=[]
            diclist = {
                '单位名称': data['baseInfo']['单位名称'],
                '单位账号': data['baseInfo']['单位账号'],
                '帐户状态': data['baseInfo']['帐户状态'],
                '当前余额': data['baseInfo']['当前余额'],
                '当年提取金额': data['baseInfo']['当年提取金额'],
                '当年缴存金额': data['baseInfo']['当年缴存金额'],
                '上年结转余额': data['baseInfo']['上年结转余额']
            }
            data['companyList'].append(diclist)
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        vc_url = VC_URL #+ str(int(time.time() * 1000))
        resp = self.s.get(vc_url,timeout=5)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])


if __name__ == '__main__':
    from services.client import TaskTestClient
    meta = {'身份证号': '410523198507216025', '职工姓名': '肖科', '密码': '111111'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()
# 	410523198410033046  陈静