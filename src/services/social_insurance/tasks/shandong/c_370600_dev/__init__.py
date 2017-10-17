#烟台社保查询：
#地址：http://ytrsj.gov.cn:8081/hsp/logonDialog_withF.jsp
#账号：370302197811184822
#密码：qq781017
import hashlib
import random
import json
import io
import base64
import datetime
from PIL import Image
from bs4 import BeautifulSoup
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask


MAIN_URL = 'http://ytrsj.gov.cn:8081/hsp/mainFrame.jsp'
LOGIN_URL = 'http://ytrsj.gov.cn:8081/hsp/logon.do'
VC_URL = 'http://ytrsj.gov.cn:8081/hsp/genAuthCode?_='
INFO_URL='http://ytrsj.gov.cn:8081/hsp/systemOSP.do'


class Task(AbsFetchTask):
    # noinspection PyAttributeOutsideInit
    task_info = dict(
        city_name="烟台",
        help="""<li>如您未在社保网站查询过您的社保信息，请到烟台社保网上服务平台完成“注册”然后再登录。</li>
                <li>如您忘记密码，可使用注册时绑定的手机号或者电子邮箱进行密码找回；当不能通过手机和电子邮箱找回密码，需去社保机构现场重置密码。</li>"""
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
        assert '密码' in params,'缺少密码'
        #assert 'vc' in params, '缺少验证码'
        # other check
    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '身份证号' not in params:
                params['身份证号'] = meta.get('身份证号')
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
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            res.append(pr)
        return res

    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._new_vc()
                vc=input('验证码：')
                self._check_login_params(params)
                id_num = params['身份证号']
                password = params['密码']
                m = hashlib.md5()
                m.update(str(password).encode(encoding="utf-8"))
                pw = m.hexdigest()

                xmlstr='<?xml version = "1.0" encoding = "UTF-8"?><p><s tempmm = "'+password+'"/></p>'
                resp = self.s.post(LOGIN_URL, data=dict(
                    method='writeMM2Temp',
                    _xmlString=xmlstr,
                    _random=random.random()
                ),headers={'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8','X-Requested-With':'XMLHttpRequest'})
                soup = BeautifulSoup(resp.content, 'html.parser')

                xmlstr = '<?xml version="1.0" encoding="UTF-8"?><p> <s userid ="'+id_num+'"/> <s usermm="'+pw+'"/><s authcode="'+vc+'"/><s yxzjlx="A"/><s appversion="81002198533703667231184339811848228729"/><s dlfs=""/></p>'
                resp = self.s.post(LOGIN_URL, data=dict(
                    method='doLogon',
                    _xmlString=xmlstr,
                    _random=random.random()
                ), headers={'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                           'X-Requested-With': 'XMLHttpRequest'})
                soup = BeautifulSoup(resp.content, 'html.parser')
                errormsg = soup.text
                if errormsg:
                    if len(errormsg)>20:
                        dicts=eval(errormsg.replace('true','"true"'))
                        self.g.usersession_uuid=dicts['__usersession_uuid']
                    else:
                        raise Exception(errormsg)

                    self.result_key=id_num
                    # 保存到meta
                    self.result_meta['用户名'] = id_num
                    self.result_meta['密码'] = password

                    self.result_identity['task_name'] = '烟台'
                    self.result_identity['target_id'] = id_num

                return
            except Exception as e:
                err_msg = str(e)
        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input', value=params.get('身份证号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            #dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            data = self.result_data
            resp = self.s.post(INFO_URL, data=dict(
                    method='returnMain',
                    __usersession_uuid=self.g.usersession_uuid,
                    _random=random.random()
                ),headers={'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8','X-Requested-With':'XMLHttpRequest'})
            soup = BeautifulSoup(resp.content, 'html.parser')
            arrcbsj=[soup.findAll('input')[6].attrs['value'],soup.findAll('input')[10].attrs['value'],soup.findAll('input')[14].attrs['value'],soup.findAll('input')[18].attrs['value'],soup.findAll('input')[22].attrs['value'],soup.findAll('input')[26].attrs['value']]
            baseinfoarr={'养老':'正常参保' if soup.findAll('input')[7].attrs['value']=='参保缴费' else '停缴',
                         '医疗': '正常参保' if soup.findAll('input')[11].attrs['value'] == '参保缴费' else '停缴',
                         '失业': '正常参保' if soup.findAll('input')[15].attrs['value'] == '参保缴费' else '停缴',
                         '工伤': '正常参保' if soup.findAll('input')[19].attrs['value'] == '参保缴费' else '停缴',
                         '生育': '正常参保' if soup.findAll('input')[23].attrs['value'] == '参保缴费' else '停缴',
                         soup.findAll('input')[25].attrs['value']: '正常参保' if soup.findAll('input')[27].attrs['value'] == '参保缴费' else '停缴'}
            data['baseInfo']={
                '姓名':soup.findAll('input')[0].attrs['value'],
                '身份证号': soup.findAll('input')[1].attrs['value'],
                '手机号码': soup.findAll('input')[2].attrs['value'],
                '家庭住址': soup.findAll('input')[3].attrs['value'],
                '通讯地址': soup.findAll('input')[4].attrs['value'],
                '五险状态': baseinfoarr,
                '开始缴费时间': min(baseinfoarr),
                "更新时间": datetime.datetime.now().strftime('%Y-%m-%d'),
                '城市名称': '烟台',
                '城市编号': '370600'
            }
            self.result_identity['target_name'] = soup.findAll('input')[0].attrs['value']
            idtstatus='停缴'
            if '正常参保' == baseinfoarr.values():
                idtstatus='正常参保'
            self.result_identity['status'] = idtstatus

            #养老


            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        #randoms=random.random()
        #vc_url = VC_URL +str(randoms) #str(int(time.time() * 1000))
        resps = json.loads(self.s.get(VC_URL).text)
        firstNum = resps['numLeftBase64']
        oprate = resps['operatorBase64']
        lastNum = resps['numRightBase64']
        equla = resps['equalsBase64']

        arr = [firstNum, oprate, lastNum, equla]
        toImage = Image.new('RGB', (110, 50), (255, 255, 255))
        for i in range(4):
            fromImge = Image.open(io.BytesIO(base64.b64decode(arr[i])))
            if (fromImge.mode == "P"):
                fromImge.convert("RGB")
            loc = (i * 22 + 15, 10)
            toImage.paste(fromImge, loc)

        toImage.show()
if __name__ == '__main__':
    from services.client import TaskTestClient
    #meta = {'身份证号': '370302197811184822', '密码': 'qq781017'}prepare_data=dict(meta=meta)
    client = TaskTestClient(Task())
    client.run()
