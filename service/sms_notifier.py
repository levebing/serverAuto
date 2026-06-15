"""
短信告警通知模块
支持阿里云、腾讯云、百度云短信接口
"""

import json
import hashlib
import hmac
import base64
import uuid
import time
import requests
from datetime import datetime
from urllib.parse import quote


class SMSNotifier:
    """短信通知基类"""
    
    def __init__(self, config):
        self.config = config
        self.provider = config.get('provider')
    
    def send_sms(self, phone_numbers, template_code, template_params):
        """
        发送短信
        :param phone_numbers: 手机号列表或单个手机号
        :param template_code: 短信模板代码
        :param template_params: 模板参数字典
        :return: (success: bool, message: str)
        """
        raise NotImplementedError
    
    def _format_phone_numbers(self, phone_numbers):
        """格式化手机号列表"""
        if isinstance(phone_numbers, str):
            return phone_numbers
        return ','.join(phone_numbers)


class AliyunSMSNotifier(SMSNotifier):
    """阿里云短信服务"""
    
    def __init__(self, config):
        super().__init__(config)
        self.access_key_id = config.get('access_key_id')
        self.access_key_secret = config.get('access_key_secret')
        self.sign_name = config.get('sign_name')
        self.endpoint = 'dysmsapi.aliyuncs.com'
    
    def _sign(self, params):
        """生成阿里云签名"""
        # 排序参数
        sorted_params = sorted(params.items())
        # 构造待签名字符串
        canonical_query_string = '&'.join(
            f"{quote(k, safe='')}={quote(str(v), safe='')}" 
            for k, v in sorted_params
        )
        string_to_sign = f"GET&%2F&{quote(canonical_query_string, safe='')}"
        # 计算签名
        key = f"{self.access_key_secret}&"
        signature = base64.b64encode(
            hmac.new(key.encode(), string_to_sign.encode(), hashlib.sha1).digest()
        ).decode()
        return signature
    
    def send_sms(self, phone_numbers, template_code, template_params):
        """发送阿里云短信"""
        try:
            params = {
                'Format': 'JSON',
                'Version': '2017-05-25',
                'AccessKeyId': self.access_key_id,
                'SignatureMethod': 'HMAC-SHA1',
                'Timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'SignatureVersion': '1.0',
                'SignatureNonce': str(uuid.uuid4()),
                'Action': 'SendSms',
                'PhoneNumbers': self._format_phone_numbers(phone_numbers),
                'SignName': self.sign_name,
                'TemplateCode': template_code,
                'TemplateParam': json.dumps(template_params)
            }
            
            params['Signature'] = self._sign(params)
            
            url = f"https://{self.endpoint}/"
            response = requests.get(url, params=params, timeout=30)
            result = response.json()
            
            if result.get('Code') == 'OK':
                return True, '发送成功'
            else:
                return False, result.get('Message', '发送失败')
                
        except Exception as e:
            return False, f'发送异常: {str(e)}'


class TencentSMSNotifier(SMSNotifier):
    """腾讯云短信服务"""
    
    def __init__(self, config):
        super().__init__(config)
        self.secret_id = config.get('secret_id')
        self.secret_key = config.get('secret_key')
        self.sign_name = config.get('sign_name')
        self.app_id = config.get('app_id')
        self.endpoint = 'sms.tencentcloudapi.com'
    
    def _sign(self, params, timestamp):
        """生成腾讯云签名"""
        # 构造待签名字符串
        service = 'sms'
        date = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')
        
        # 1. 构造规范请求
        http_method = 'POST'
        canonical_uri = '/'
        canonical_querystring = ''
        
        headers = {
            'content-type': 'application/json; charset=utf-8',
            'host': self.endpoint
        }
        canonical_headers = '\n'.join(f"{k}:{v}" for k, v in sorted(headers.items())) + '\n'
        signed_headers = ';'.join(headers.keys())
        
        payload = json.dumps(params)
        hashed_payload = hashlib.sha256(payload.encode()).hexdigest()
        
        canonical_request = f"{http_method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{hashed_payload}"
        
        # 2. 构造待签名字符串
        credential_scope = f"{date}/{service}/tc3_request"
        string_to_sign = f"TC3-HMAC-SHA256\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
        
        # 3. 计算签名
        secret_date = hmac.new(f"TC3{self.secret_key}".encode(), date.encode(), hashlib.sha256).digest()
        secret_service = hmac.new(secret_date, service.encode(), hashlib.sha256).digest()
        secret_signing = hmac.new(secret_service, b'tc3_request', hashlib.sha256).digest()
        signature = hmac.new(secret_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()
        
        return signature, credential_scope
    
    def send_sms(self, phone_numbers, template_code, template_params):
        """发送腾讯云短信"""
        try:
            timestamp = int(time.time())
            date = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')
            
            # 构造请求参数
            params = {
                "PhoneNumberSet": phone_numbers if isinstance(phone_numbers, list) else [phone_numbers],
                "TemplateID": template_code,
                "Sign": self.sign_name,
                "TemplateParamSet": list(template_params.values()) if template_params else [],
                "SmsSdkAppid": self.app_id
            }
            
            signature, credential_scope = self._sign(params, timestamp)
            
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'Host': self.endpoint,
                'X-TC-Action': 'SendSms',
                'X-TC-Version': '2021-01-11',
                'X-TC-Timestamp': str(timestamp),
                'Authorization': f"TC3-HMAC-SHA256 Credential={self.secret_id}/{credential_scope}, SignedHeaders=content-type;host, Signature={signature}"
            }
            
            url = f"https://{self.endpoint}/"
            response = requests.post(url, headers=headers, json=params, timeout=30)
            result = response.json()
            
            if result.get('Response', {}).get('SendStatusSet', [{}])[0].get('Code') == 'Ok':
                return True, '发送成功'
            else:
                error = result.get('Response', {}).get('Error', {})
                return False, error.get('Message', '发送失败')
                
        except Exception as e:
            return False, f'发送异常: {str(e)}'


class BaiduSMSNotifier(SMSNotifier):
    """百度云短信服务"""
    
    def __init__(self, config):
        super().__init__(config)
        self.access_key_id = config.get('access_key_id')
        self.secret_access_key = config.get('secret_access_key')
        self.sign_name = config.get('sign_name')
        self.endpoint = 'smsv3.bj.baidubce.com'
    
    def _sign(self, timestamp, expiration=1800):
        """生成百度云签名"""
        # 构造签名字符串
        auth_string_prefix = f"bce-auth-v1/{self.access_key_id}/{timestamp}/{expiration}"
        signing_key = hmac.new(
            self.secret_access_key.encode(),
            auth_string_prefix.encode(),
            hashlib.sha256
        ).hexdigest()
        return signing_key, auth_string_prefix
    
    def send_sms(self, phone_numbers, template_code, template_params):
        """发送百度云短信"""
        try:
            timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            signing_key, auth_string_prefix = self._sign(timestamp)
            
            # 构造请求头
            headers = {
                'Host': self.endpoint,
                'Content-Type': 'application/json',
                'x-bce-date': timestamp,
                'Authorization': f"{auth_string_prefix}/host/x-bce-date/{signing_key}"
            }
            
            # 构造请求体
            payload = {
                'mobile': self._format_phone_numbers(phone_numbers),
                'template': template_code,
                'signatureId': self.sign_name,
                'contentVar': template_params
            }
            
            url = f"https://{self.endpoint}/api/v3/sendSms"
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            result = response.json()
            
            if result.get('code') == '1000':
                return True, '发送成功'
            else:
                return False, result.get('message', '发送失败')
                
        except Exception as e:
            return False, f'发送异常: {str(e)}'


class CustomSMSNotifier(SMSNotifier):
    """自研短信服务"""
    
    def __init__(self, config):
        super().__init__(config)
        self.api_url = config.get('custom_api_url')
        self.headers = config.get('custom_headers', {})
        if isinstance(self.headers, str):
            try:
                self.headers = json.loads(self.headers)
            except:
                self.headers = {}
    
    def send_sms(self, phone_numbers, template_code, template_params):
        """发送自研短信服务"""
        try:
            if not self.api_url:
                return False, '未配置短信接口URL'
            
            # 构造请求头
            headers = {
                'Content-Type': 'application/json',
                **self.headers
            }
            
            # 构造请求体
            payload = {
                'phone_numbers': self._format_phone_numbers(phone_numbers),
                'template_code': template_code,
                'template_params': template_params
            }
            
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            
            # 尝试解析响应
            try:
                result = response.json()
                # 检查常见的成功状态码
                if result.get('success') or result.get('code') == 0 or result.get('status') == 'success':
                    return True, result.get('message', '发送成功')
                else:
                    return False, result.get('message', '发送失败')
            except:
                # 如果不是JSON响应，检查HTTP状态码
                if response.status_code == 200:
                    return True, '发送成功'
                else:
                    return False, f'HTTP错误: {response.status_code}'
                    
        except Exception as e:
            return False, f'发送异常: {str(e)}'


def get_sms_notifier(config):
    """
    根据配置获取对应的短信通知器
    :param config: 短信配置字典
    :return: SMSNotifier实例
    """
    provider = config.get('provider', '').lower()
    
    if provider == 'aliyun':
        return AliyunSMSNotifier(config)
    elif provider == 'tencent':
        return TencentSMSNotifier(config)
    elif provider == 'baidu':
        return BaiduSMSNotifier(config)
    elif provider == 'custom':
        return CustomSMSNotifier(config)
    else:
        raise ValueError(f'不支持的短信服务商: {provider}')


def send_alert_sms(phone_numbers, alert_type, alert_data, config):
    """
    发送告警短信
    :param phone_numbers: 接收手机号
    :param alert_type: 告警类型 (inspection/fault/system)
    :param alert_data: 告警数据字典
    :param config: 短信配置
    :return: (success: bool, message: str)
    """
    try:
        notifier = get_sms_notifier(config)
        
        # 根据告警类型选择模板
        template_code = config.get(f'{alert_type}_template_code')
        if not template_code:
            return False, f'未配置{alert_type}类型的短信模板'
        
        # 构造模板参数
        template_params = _build_template_params(alert_type, alert_data)
        
        return notifier.send_sms(phone_numbers, template_code, template_params)
        
    except Exception as e:
        return False, f'发送失败: {str(e)}'


def _build_template_params(alert_type, alert_data):
    """
    构建短信模板参数
    """
    params = {}
    
    if alert_type == 'inspection':
        # 巡检告警
        params = {
            'server_name': alert_data.get('server_name', ''),
            'server_ip': alert_data.get('server_ip', ''),
            'alert_item': alert_data.get('alert_item', ''),
            'alert_value': alert_data.get('alert_value', ''),
            'threshold': alert_data.get('threshold', ''),
            'time': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    elif alert_type == 'fault':
        # 故障告警
        params = {
            'fault_name': alert_data.get('fault_name', ''),
            'fault_level': alert_data.get('fault_level', ''),
            'server_name': alert_data.get('server_name', ''),
            'occurrence_time': alert_data.get('occurrence_time', ''),
            'description': alert_data.get('description', '')
        }
    elif alert_type == 'system':
        # 系统告警
        params = {
            'alert_title': alert_data.get('alert_title', ''),
            'alert_content': alert_data.get('alert_content', ''),
            'time': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    
    return params
