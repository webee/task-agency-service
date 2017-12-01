import json
import time
from bs4 import BeautifulSoup
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask

LOGIN_URL = 'http://219.147.7.52:89/Controller/login.ashx'
VC_URL='http://219.147.7.52:89/Controller/Image.aspx'
INFO_URL='http://219.147.7.52:89/Controller/GR/gjcx/gjjzlcx.ashx'
ENTER_URL='http://219.147.7.52:89/Controller/GR/gjcx/dwjbxx.ashx'
MINGXI_URL='http://219.147.7.52:89/Controller/GR/gjcx/gjcx.ashx'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="青岛",
        help="""<li>首次登陆密码默认为住房公积金个人编号后6位。</li>
            <li>住房公积金个人编号取得方式：
                本人持住房公积金联名卡到所属银行自助终端查询；本人持身份证到住房公积金管理中心各管理处查询；本人到单位住房公积金经办人处查询。
            </li>""",
        developers = [{'name': '卜圆圆', 'email': 'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {'User-Agent':'Mozilla/5.0 (iPad; CPU OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1'}

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '身份证号' in params, '缺少身份证号'
        assert '密码' in params, '缺少密码'

        # other check
        身份证号 = params['身份证号']
        密码 = params['密码']
        if len(密码) < 6:
            raise InvalidParamsError('身份证号或密码错误')
        if 身份证号.isdigit():
            if len(身份证号) <15:
                raise InvalidParamsError('身份证号错误')
            return
        raise InvalidParamsError('身份证号或密码错误')

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                id_num = params['身份证号']
                password = params['密码']
                vc = params['vc']
                data={
                    'name': id_num,
                    'password': password,
                    'yzm':vc,
                    'logintype': '0',
                    'usertype': '10',
                    'dn':'',
                    'signdata':'',
                    '1': 'y'
                }
                resp = self.s.post(LOGIN_URL, data=data,timeout=10)
                soup = BeautifulSoup(resp.content, 'html.parser')
                successinfo=json.loads(soup.text)
                if successinfo['success']:
                    print("登录成功！")
                else:
                    return_message = successinfo['msg']
                    raise InvalidParamsError(return_message)

                self.result_key = params.get('身份证号')
                # 保存到meta
                self.result_meta['身份证号'] = params.get('身份证号')
                self.result_meta['密码'] = params.get('密码')
                self.result_identity['task_name'] = '青岛'

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input', placeholder='身份证号', value=params.get('身份证号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch(self):
        try:
            # 基本信息
            resp = self.s.get(INFO_URL,timeout=15)
            soup = BeautifulSoup(resp.content, 'html.parser')
            if len(soup.text)<18:
                raise InvalidParamsError('第一次登录，请去官网修改密码！')
            info = json.loads(soup.text)
            data = self.result_data
            data['baseInfo'] = {
                '城市名称': '青岛',
                '城市编号': '370200',
                '证件号': info['sfz'],
                '证件类型': '身份证',
                '个人账号':info['khh'],
                '姓名':info['hm'],
                '帐户状态': info['zt'],
                '手机号': info['sjhm'],
                '开户日期': info['khrq'].replace('-',''),
                '月应缴额': info['gze'],
                '单位缴存比例': info['dwjcbl']+'%',
                '个人缴存比例': info['grjcbl']+'%',
                '当前余额': info['zhye'],
                '联名卡号': info['kh'],
                '联名卡发卡行': info['hb'],
                '联名卡登记日期': info['djrq'],
                '单位月缴存额': info['dwyhjje'],
                '个人月缴存额': info['gryhjje'],
                '更新时间': time.strftime("%Y-%m-%d", time.localtime())
            }
            self.result_identity['target_name'] = data['baseInfo']['姓名']
            self.result_identity['target_id'] = data['baseInfo']['证件号']
            self.result_identity['status'] = data['baseInfo']['帐户状态']

            resp = self.s.get(ENTER_URL,timeout=15)
            soup = BeautifulSoup(resp.content, 'html.parser')
            enterinfo = json.loads(soup.text)
            data['companyList']=[]
            entdic={
                "单位名称": enterinfo['hm'],
                "单位编号": enterinfo['khh'],
                "单位地址": enterinfo['dz'],
                "经办部门": enterinfo['jbbm'],
                "所在市区": enterinfo['szqs'],
                "成立日期": enterinfo['clrq'],
                "组织机构代码": enterinfo['zzdm'],
                "单位性质": enterinfo['dwxz'],
                "营业执照编号": enterinfo['yyzz'],
                "法人资格": enterinfo['frzg'],
                "法人代表": enterinfo['frdb'],
                "发薪日": enterinfo['fxrq'],
                "主管单位": enterinfo['zgdw'],
                "单位传真": enterinfo['cz'],
                "单位邮编": enterinfo['yb'],
                '帐户状态': info['zt'],
                '当前余额': info['zhye']
            }
            data['companyList'].append(entdic)
            #明细
            datas={
                'dt':time.time() * 1000,
                'm': 'grjcmx',
                'start': '1900-01-01',
                'end':time.strftime("%Y-%m-%d", time.localtime()),
                'page': '1',
                'rows': '20000',
                'sort': 'csrq',
                'order': 'desc'
            }
            resp = self.s.post(MINGXI_URL,data=datas,timeout=15)
            soup = BeautifulSoup(resp.content, 'html.parser')
            mingxiinfo = json.loads(soup.text)
            data['detail'] = {}
            data['detail']['data'] = {}
            years = ''
            months = ''
            hjtype=0
            hjcs=0
            hjje=''
            hjrq=''
            for i in range(0,int(mingxiinfo['total'])):
                mxdic=mingxiinfo['rows'][i]
                arr = []
                dic = {
                    '时间': mxdic['csrq'],
                    '单位名称': mxdic['hm'],
                    '支出': 0,
                    '收入':str(float(mxdic['grje'])+float(mxdic['dwje'])) ,
                    '汇缴年月': mxdic['ssny'],
                    '余额': 0,
                    '类型': mxdic['jjyyname'],
                    '单据状态':  mxdic['ztname'],
                    '单位金额': mxdic['dwje'],
                    '个人金额': mxdic['grje'],
                    '结算方式': mxdic['jslxname']
                }
                if mxdic['ssny']:
                    hjcs=hjcs+1
                    if hjtype==0:
                        hjtype=1
                        hjje=str(float(mxdic['grje'])+float(mxdic['dwje']))
                        hjrq= mxdic['ssny']
                times = mxdic['csrq'][:7].replace('-', '')
                if years != times[:4]:
                    years = times[:4]
                    data['detail']['data'][years] = {}
                    if months != times[-2:]:
                        months = times[-2:]
                        data['detail']['data'][years][months] = {}
                else:
                    if months != times[-2:]:
                        months = times[-2:]
                        data['detail']['data'][years][months] = {}
                    else:
                        arr = data['detail']['data'][years][months]
                arr.append(dic)
                data['detail']['data'][years][months] = arr
            data['baseInfo']['最近汇缴日期'] = hjrq
            data['baseInfo']['最近汇缴金额'] = hjje
            data['baseInfo']['累计汇缴次数'] = hjcs

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        #vc_url = VC_URL  # + str(int(time.time() * 1000))
        resp = self.s.get(VC_URL,timeout=5)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])
if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'身份证号': '230127199007171013', '密码': '784610'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

#'身份证号': '370881198207145816', '密码': '080707'