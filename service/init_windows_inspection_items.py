#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化Windows巡检项
添加常见的Windows系统巡检命令
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_connection, DATABASE_TYPE

def init_windows_inspection_items():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Windows巡检项列表
    windows_items = [
        {
            'name': 'CPU使用率',
            'command': '(Get-WmiObject -Class Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average',
            'description': '获取CPU使用率',
            'os_type': 'windows'
        },
        {
            'name': '内存使用情况',
            'command': '$total = (Get-WmiObject -Class Win32_ComputerSystem).TotalPhysicalMemory; $free = (Get-WmiObject -Class Win32_OperatingSystem).FreePhysicalMemory * 1KB; $used = $total - $free; "Total: {0:N2} GB, Used: {1:N2} GB, Free: {2:N2} GB, Usage: {3:N1}%".format($total/1GB, $used/1GB, $free/1GB, ($used/$total)*100)',
            'description': '获取内存使用情况',
            'os_type': 'windows'
        },
        {
            'name': '磁盘使用情况',
            'command': 'Get-WmiObject -Class Win32_LogicalDisk -Filter "DriveType=3" | Select-Object DeviceID, @{n="Size(GB)";e={[math]::Round($_.Size/1GB,2)}}, @{n="Free(GB)";e={[math]::Round($_.FreeSpace/1GB,2)}}, @{n="Usage%";e={[math]::Round((1-$_.FreeSpace/$_.Size)*100,1)}}',
            'description': '获取磁盘使用情况',
            'os_type': 'windows'
        },
        {
            'name': '系统时间',
            'command': 'Get-Date -Format "yyyy-MM-dd HH:mm:ss"',
            'description': '获取系统当前时间',
            'os_type': 'windows'
        },
        {
            'name': '操作系统版本',
            'command': '$os = Get-WmiObject -Class Win32_OperatingSystem; $os.Caption + " - Build " + $os.BuildNumber',
            'description': '获取操作系统版本信息',
            'os_type': 'windows'
        },
        {
            'name': '系统服务状态',
            'command': 'Get-Service | Where-Object { $_.Status -eq "Running" } | Select-Object Name, DisplayName, Status | Format-Table -AutoSize',
            'description': '获取运行中的系统服务',
            'os_type': 'windows'
        },
        {
            'name': '网络连接状态',
            'command': 'Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, LinkSpeed | Format-Table -AutoSize',
            'description': '获取网络适配器状态',
            'os_type': 'windows'
        },
        {
            'name': '登录用户',
            'command': 'Get-WmiObject -Class Win32_ComputerSystem | Select-Object UserName',
            'description': '获取当前登录用户',
            'os_type': 'windows'
        },
        {
            'name': '进程列表',
            'command': 'Get-Process | Select-Object Name, Id, WorkingSet | Sort-Object WorkingSet -Descending | Select-Object -First 10',
            'description': '获取内存占用最高的前10个进程',
            'os_type': 'windows'
        },
        {
            'name': '最近事件日志',
            'command': 'Get-EventLog -LogName System -EntryType Error -Newest 5 | Select-Object TimeGenerated, Source, Message',
            'description': '获取最近5条系统错误日志',
            'os_type': 'windows'
        },
        {
            'name': '系统启动时间',
            'command': '$bootTime = (Get-WmiObject -Class Win32_OperatingSystem).LastBootUpTime; [Management.ManagementDateTimeConverter]::ToDateTime($bootTime)',
            'description': '获取系统上次启动时间',
            'os_type': 'windows'
        },
        {
            'name': '页面文件使用',
            'command': 'Get-WmiObject -Class Win32_PageFileUsage | Select-Object Name, CurrentUsage, PeakUsage',
            'description': '获取页面文件使用情况',
            'os_type': 'windows'
        }
    ]
    
    # 添加巡检项
    for item in windows_items:
        # 检查是否已存在
        if DATABASE_TYPE != 'sqlite':
            cursor.execute('SELECT id FROM inspection_items WHERE name = %s AND os_type = %s AND is_deleted = 0', 
                        (item['name'], item['os_type']))
        else:
            cursor.execute('SELECT id FROM inspection_items WHERE name = ? AND os_type = ? AND is_deleted = 0', 
                        (item['name'], item['os_type']))
        
        existing = cursor.fetchone()
        
        if not existing:
            if DATABASE_TYPE != 'sqlite':
                cursor.execute('''
                    INSERT INTO inspection_items (name, command, description, os_type, sort_order, is_enabled, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (item['name'], item['command'], item['description'], item['os_type']))
            else:
                cursor.execute('''
                    INSERT INTO inspection_items (name, command, description, os_type, sort_order, is_enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (item['name'], item['command'], item['description'], item['os_type']))
            print(f"添加巡检项: {item['name']}")
    
    conn.commit()
    conn.close()
    print("Windows巡检项初始化完成！")

if __name__ == '__main__':
    init_windows_inspection_items()