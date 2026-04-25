import paramiko
import tempfile
import os
from datetime import datetime
from config import MAX_ALERT_THRESHOLD

class ServerInspector:
    def __init__(self, ip, port, username, private_key_content=None, password=None):
        self.ip = ip
        self.port = port
        self.username = username
        self.private_key_content = private_key_content
        self.password = password
        self.ssh = None
        self.temp_key_path = None
        self.last_error = ""
    
    def connect(self):
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.private_key_content:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
                    f.write(self.private_key_content.decode('utf-8') if isinstance(self.private_key_content, bytes) else self.private_key_content)
                    self.temp_key_path = f.name
                
                try:
                    private_key = paramiko.RSAKey.from_private_key_file(self.temp_key_path)
                except Exception as rsa_error:
                    try:
                        private_key = paramiko.DSSKey.from_private_key_file(self.temp_key_path)
                    except Exception as dss_error:
                        try:
                            private_key = paramiko.ECDSAKey.from_private_key_file(self.temp_key_path)
                        except Exception as ecdsa_error:
                            try:
                                private_key = paramiko.Ed25519Key.from_private_key_file(self.temp_key_path)
                            except Exception as ed_error:
                                self.last_error = f"密钥文件解析失败: RSA={str(rsa_error)}, DSS={str(dss_error)}, ECDSA={str(ecdsa_error)}, Ed25519={str(ed_error)}"
                                return False
                
                try:
                    self.ssh.connect(self.ip, port=self.port, username=self.username, pkey=private_key, timeout=10, banner_timeout=10)
                except paramiko.AuthenticationException:
                    self.last_error = "SSH认证失败：用户名或密钥不正确"
                    return False
                except paramiko.SSHException as e:
                    self.last_error = f"SSH连接异常: {str(e)}"
                    return False
                except ConnectionRefusedError:
                    self.last_error = f"连接被拒绝：服务器 {self.ip}:{self.port} 未开启SSH服务或端口不正确"
                    return False
                except TimeoutError:
                    self.last_error = f"连接超时：无法连接到 {self.ip}:{self.port}，请检查网络和防火墙"
                    return False
                except Exception as e:
                    self.last_error = f"秘钥登录失败: {str(e)}"
                    return False
            else:
                if not self.password:
                    self.last_error = "未配置密码或秘钥文件"
                    return False
                
                try:
                    self.ssh.connect(self.ip, port=self.port, username=self.username, password=self.password, timeout=10, banner_timeout=10)
                except paramiko.AuthenticationException:
                    self.last_error = "SSH认证失败：用户名或密码不正确"
                    return False
                except paramiko.SSHException as e:
                    self.last_error = f"SSH连接异常: {str(e)}"
                    return False
                except ConnectionRefusedError:
                    self.last_error = f"连接被拒绝：服务器 {self.ip}:{self.port} 未开启SSH服务或端口不正确"
                    return False
                except TimeoutError:
                    self.last_error = f"连接超时：无法连接到 {self.ip}:{self.port}，请检查网络和防火墙"
                    return False
                except Exception as e:
                    self.last_error = f"密码登录失败: {str(e)}"
                    return False
            
            return True
        except Exception as e:
            self.last_error = f"连接失败: {str(e)}"
            return False
    
    def disconnect(self):
        if self.ssh:
            self.ssh.close()
        if self.temp_key_path and os.path.exists(self.temp_key_path):
            os.unlink(self.temp_key_path)
    
    def execute_command(self, command):
        if not self.ssh:
            return None
        
        try:
            stdin, stdout, stderr = self.ssh.exec_command(command)
            output = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()
            return output if output else error
        except Exception as e:
            return None
    
    def get_disk_usage(self):
        output = self.execute_command('df -h')
        if not output:
            return None
        
        lines = output.strip().split('\n')[1:]
        disk_info = []
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 6:
                filesystem = parts[0]
                size = parts[1]
                used = parts[2]
                available = parts[3]
                usage_percent = parts[4]
                mount_point = parts[-1]
                
                if not self.is_useless_filesystem(filesystem):
                    disk_info.append({
                        'filesystem': filesystem,
                        'size': size,
                        'used': used,
                        'available': available,
                        'usage_percent': int(usage_percent.rstrip('%')),
                        'mount_point': mount_point
                    })
        
        return disk_info
    
    def is_useless_filesystem(self, filesystem):
        useless_patterns = [
            'tmpfs',
            'devtmpfs',
            'overlay',
            'shm',
            'cgroup',
            'proc',
            'sysfs',
            'devpts',
            'squashfs',
            '/dev/loop'
        ]
        
        for pattern in useless_patterns:
            if pattern in filesystem:
                return True
        return False
    
    def get_memory_usage(self):
        output = self.execute_command('free -h')
        if not output:
            return None
        
        lines = output.strip().split('\n')
        memory_info = {}
        
        for line in lines:
            if line.startswith('Mem:'):
                parts = line.split()
                memory_info['total'] = parts[1]
                memory_info['used'] = parts[2]
                memory_info['available'] = parts[-1]
                break
        
        output = self.execute_command("free | grep Mem | awk '{print $3/$2 * 100}'")
        if output:
            memory_info['usage_percent'] = int(float(output.strip()))
        
        return memory_info
    
    def get_cpu_usage(self):
        output = self.execute_command("top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'")
        if output:
            return int(float(output.strip()))
        return None
    
    def get_system_time(self):
        output = self.execute_command('date "+%Y-%m-%d %H:%M:%S"')
        if output:
            return output.strip()
        return None
    
    def get_os_version(self):
        output = self.execute_command('cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null || uname -a')
        if output:
            return output.strip()
        return None
    
    def inspect(self):
        if not self.connect():
            return None, self.last_error if self.last_error else "连接服务器失败"
        
        try:
            disk_info = self.get_disk_usage()
            memory_info = self.get_memory_usage()
            cpu_usage = self.get_cpu_usage()
            system_time = self.get_system_time()
            os_version = self.get_os_version()
            inspection_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            alerts = []
            
            if disk_info:
                for disk in disk_info:
                    if disk['usage_percent'] >= MAX_ALERT_THRESHOLD:
                        alerts.append(f"磁盘 {disk['mount_point']} 使用率 {disk['usage_percent']}%")
            
            if memory_info and memory_info.get('usage_percent') >= MAX_ALERT_THRESHOLD:
                alerts.append(f"内存使用率 {memory_info['usage_percent']}%")
            
            alert_content = '; '.join(alerts) if alerts else '无告警'
            
            description = f"========== 服务器巡检报告 ==========\n"
            description += f"服务器IP: {self.ip}\n"
            description += f"巡检时间: {inspection_time}\n"
            description += f"=====================================\n\n"
            
            description += "【操作系统信息】\n"
            if os_version:
                description += f"{os_version}\n"
            else:
                description += "无法获取操作系统版本\n"
            description += "\n"
            
            description += "【系统时间】\n"
            description += f"{system_time}\n\n"
            
            description += "【CPU使用率】\n"
            description += f"{cpu_usage}%\n\n"
            
            description += "【内存使用情况】\n"
            if memory_info:
                memory_status = "⚠️" if memory_info.get('usage_percent') >= MAX_ALERT_THRESHOLD else ""
                description += f"总计: {memory_info['total']}\n"
                description += f"已用: {memory_info['used']}\n"
                description += f"可用: {memory_info['available']}\n"
                description += f"使用率: {memory_info.get('usage_percent', '未知')}% {memory_status}\n"
            else:
                description += "无法获取内存信息\n"
            description += "\n"
            
            description += "【磁盘使用情况】\n"
            if disk_info:
                for disk in disk_info:
                    status = "⚠️" if disk['usage_percent'] >= MAX_ALERT_THRESHOLD else ""
                    description += f"  {disk['mount_point']}\n"
                    description += f"    文件系统: {disk['filesystem']}\n"
                    description += f"    总计: {disk['size']}\n"
                    description += f"    已用: {disk['used']}\n"
                    description += f"    可用: {disk['available']}\n"
                    description += f"    使用率: {disk['usage_percent']}% {status}\n"
            else:
                description += "无法获取磁盘信息\n"
            
            if alerts:
                description += f"\n【告警内容】\n"
                description += "⚠️ " + alert_content
            else:
                description += f"\n【告警内容】\n"
                description += "✅ 无告警"
            
            description += f"\n\n=====================================\n"
            
            return {
                'disk_usage': str(disk_info),
                'memory_usage': str(memory_info),
                'cpu_usage': str(cpu_usage),
                'system_time': system_time,
                'os_version': os_version,
                'inspection_time': inspection_time,
                'alert_content': alert_content,
                'description': description
            }, None
        finally:
            self.disconnect()