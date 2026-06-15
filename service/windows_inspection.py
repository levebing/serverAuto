import winrm
from datetime import datetime
from config import MAX_ALERT_THRESHOLD
from database import get_all_inspection_items

class WindowsServerInspector:
    def __init__(self, ip, port, username, password=None):
        self.ip = ip
        self.port = port if port else 5985
        self.username = username
        self.password = password
        self.session = None
        self.last_error = ""
    
    def connect(self):
        try:
            # 构建WinRM连接URL
            protocol = 'http' if self.port == 5985 else 'https'
            url = f"{protocol}://{self.ip}:{self.port}/wsman"
            
            self.session = winrm.Session(
                url,
                auth=(self.username, self.password),
                transport='ntlm',
                server_cert_validation='ignore'
            )
            return True
        except Exception as e:
            self.last_error = f"WinRM连接失败: {str(e)}"
            return False
    
    def disconnect(self):
        # WinRM session不需要显式关闭
        self.session = None
    
    def execute_command(self, command):
        if not self.session:
            return None
        
        try:
            result = self.session.run_ps(command)
            if result.status_code == 0:
                return result.std_out.decode('utf-8').strip()
            else:
                return result.std_err.decode('utf-8').strip()
        except Exception as e:
            return None
    
    def get_disk_usage(self):
        # PowerShell命令获取磁盘使用情况
        command = '''
            Get-WmiObject -Class Win32_LogicalDisk -Filter "DriveType=3" | 
            Select-Object DeviceID, Size, FreeSpace, VolumeName |
            ForEach-Object {
                $sizeGB = [math]::Round($_.Size / 1GB, 2)
                $freeGB = [math]::Round($_.FreeSpace / 1GB, 2)
                $usedGB = [math]::Round(($_.Size - $_.FreeSpace) / 1GB, 2)
                $usedPercent = [math]::Round((($_.Size - $_.FreeSpace) / $_.Size) * 100, 2)
                [PSCustomObject]@{
                    DeviceID = $_.DeviceID
                    Size = "$sizeGB GB"
                    Used = "$usedGB GB"
                    Available = "$freeGB GB"
                    UsagePercent = $usedPercent
                    VolumeName = $_.VolumeName
                }
            } | ConvertTo-Json
        '''
        output = self.execute_command(command)
        if not output:
            return None
        
        try:
            import json
            disks = json.loads(output)
            disk_info = []
            for disk in disks:
                disk_info.append({
                    'filesystem': disk['DeviceID'],
                    'size': disk['Size'],
                    'used': disk['Used'],
                    'available': disk['Available'],
                    'usage_percent': float(disk['UsagePercent']),
                    'mount_point': disk['VolumeName'] if disk['VolumeName'] else disk['DeviceID']
                })
            return disk_info
        except:
            return None
    
    def get_memory_usage(self):
        # PowerShell命令获取内存使用情况
        command = '''
            $total = (Get-WmiObject -Class Win32_ComputerSystem).TotalPhysicalMemory
            $free = (Get-WmiObject -Class Win32_OperatingSystem).FreePhysicalMemory * 1KB
            $used = $total - $free
            $totalGB = [math]::Round($total / 1GB, 2)
            $usedGB = [math]::Round($used / 1GB, 2)
            $freeGB = [math]::Round($free / 1GB, 2)
            $usedPercent = [math]::Round(($used / $total) * 100, 2)
            [PSCustomObject]@{
                Total = "$totalGB GB"
                Used = "$usedGB GB"
                Available = "$freeGB GB"
                UsagePercent = $usedPercent
            } | ConvertTo-Json
        '''
        output = self.execute_command(command)
        if not output:
            return None
        
        try:
            import json
            memory = json.loads(output)
            return {
                'total': memory['Total'],
                'used': memory['Used'],
                'available': memory['Available'],
                'usage_percent': int(float(memory['UsagePercent']))
            }
        except:
            return None
    
    def get_cpu_usage(self):
        # PowerShell命令获取CPU使用率
        command = '''
            $cpuUsage = (Get-WmiObject -Class Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
            [math]::Round($cpuUsage, 0)
        '''
        output = self.execute_command(command)
        if output:
            try:
                return int(float(output.strip()))
            except:
                return None
        return None
    
    def get_system_time(self):
        # PowerShell命令获取系统时间
        command = 'Get-Date -Format "yyyy-MM-dd HH:mm:ss"'
        output = self.execute_command(command)
        if output:
            return output.strip()
        return None
    
    def get_os_version(self):
        # PowerShell命令获取操作系统版本
        command = '''
            $os = Get-WmiObject -Class Win32_OperatingSystem
            $os.Caption + " " + $os.Version
        '''
        output = self.execute_command(command)
        if output:
            return output.strip()
        return None
    
    def inspect(self):
        if not self.connect():
            return None, self.last_error if self.last_error else "连接服务器失败"
        
        try:
            # 从数据库获取Windows相关的巡检项
            inspection_items = get_all_inspection_items(os_type='windows')
            
            inspection_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 执行所有巡检项
            results = {}
            alerts = []
            
            for item in inspection_items:
                item_id, name, command, description, os_type, sort_order, is_enabled = item
                if is_enabled:
                    output = self.execute_command(command)
                    results[name] = output
                    
                    # 特殊处理CPU和内存使用率的告警
                    if name == 'CPU使用率' and output:
                        try:
                            cpu_percent = float(output.strip())
                            if cpu_percent >= MAX_ALERT_THRESHOLD:
                                alerts.append(f"CPU使用率 {cpu_percent}%")
                        except:
                            pass
                    elif name == '内存使用情况' and output:
                        try:
                            import json
                            memory = json.loads(output)
                            percent = float(memory['UsagePercent'])
                            if percent >= MAX_ALERT_THRESHOLD:
                                alerts.append(f"内存使用率 {percent:.1f}%")
                        except:
                            pass
                    elif name == '磁盘使用情况' and output:
                        try:
                            import json
                            disks = json.loads(output)
                            for disk in disks:
                                percent = float(disk['UsagePercent'])
                                if percent >= MAX_ALERT_THRESHOLD:
                                    alerts.append(f"{disk['DeviceID']}磁盘使用率 {percent:.1f}%")
                        except:
                            pass
            
            # 执行内置巡检项
            disk_info = self.get_disk_usage()
            memory_info = self.get_memory_usage()
            cpu_usage = self.get_cpu_usage()
            system_time = self.get_system_time()
            os_version = self.get_os_version()
            
            self.disconnect()
            
            return {
                'inspection_time': inspection_time,
                'disk_usage': disk_info,
                'memory_usage': memory_info,
                'cpu_usage': cpu_usage,
                'system_time': system_time,
                'os_version': os_version,
                'custom_results': results,
                'alerts': alerts
            }, None
        except Exception as e:
            self.disconnect()
            return None, str(e)