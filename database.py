import sqlite3
from datetime import datetime, timedelta
from config import DATABASE_PATH

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sort_order INTEGER DEFAULT 0,
            is_deleted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ip TEXT NOT NULL,
            port INTEGER DEFAULT 22,
            username TEXT NOT NULL,
            private_key_content BLOB,
            password TEXT,
            group_id INTEGER DEFAULT 1,
            remark TEXT,
            is_deleted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inspection_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            disk_usage TEXT,
            memory_usage TEXT,
            cpu_usage TEXT,
            system_time TEXT,
            os_version TEXT,
            inspection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            alert_content TEXT,
            report_content TEXT,
            inspection_result TEXT,
            is_deleted INTEGER DEFAULT 0,
            FOREIGN KEY (server_id) REFERENCES servers(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            cron_expression TEXT,
            is_enabled INTEGER DEFAULT 1,
            is_deleted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (server_id) REFERENCES servers(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT,
            group_id INTEGER,
            group_name TEXT,
            report_name TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            FOREIGN KEY (group_id) REFERENCES groups(id)
        )
    ''')
    
    cursor.execute('SELECT COUNT(*) FROM groups')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO groups (name) VALUES (?)', ('默认分组',))
    
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DATABASE_PATH)

def add_group(name):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO groups (name) VALUES (?)', (name,))
        conn.commit()
        group_id = cursor.lastrowid
        conn.close()
        return group_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

def get_all_groups():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, sort_order FROM groups WHERE is_deleted = 0 ORDER BY sort_order ASC, created_at DESC')
    groups = cursor.fetchall()
    conn.close()
    return groups

def get_group_by_id(group_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM groups WHERE id = ? AND is_deleted = 0', (group_id,))
    group = cursor.fetchone()
    conn.close()
    return group

def delete_group(group_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE servers SET group_id = 1 WHERE group_id = ?', (group_id,))
    cursor.execute('UPDATE groups SET is_deleted = 1 WHERE id = ?', (group_id,))
    conn.commit()
    conn.close()

def update_group(group_id, name):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE groups SET name = ? WHERE id = ?', (name, group_id))
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        return rows_affected > 0
    except sqlite3.IntegrityError:
        conn.close()
        return None

def add_server(name, ip, port, username, group_id=1, remark='', private_key_content=None, password=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO servers (name, ip, port, username, group_id, remark, private_key_content, password)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, ip, port, username, group_id, remark, private_key_content, password))
    conn.commit()
    server_id = cursor.lastrowid
    conn.close()
    return server_id

def get_all_servers(group_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if group_id and group_id != 'all':
        cursor.execute('''
            SELECT s.id, s.name, s.ip, s.port, s.username, s.group_id, g.name as group_name, s.remark, s.created_at 
            FROM servers s LEFT JOIN groups g ON s.group_id = g.id 
            WHERE s.group_id = ? AND s.is_deleted = 0 ORDER BY s.created_at DESC
        ''', (group_id,))
    else:
        cursor.execute('''
            SELECT s.id, s.name, s.ip, s.port, s.username, s.group_id, g.name as group_name, s.remark, s.created_at 
            FROM servers s LEFT JOIN groups g ON s.group_id = g.id 
            WHERE s.is_deleted = 0 ORDER BY s.created_at DESC
        ''')
    servers = cursor.fetchall()
    conn.close()
    return servers

def get_server_by_id(server_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM servers WHERE id = ? AND is_deleted = 0', (server_id,))
    server = cursor.fetchone()
    conn.close()
    return server

def update_server(server_id, name, ip, port, username, group_id=1, remark='', private_key_content=None, password=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE servers SET name=?, ip=?, port=?, username=?, group_id=?, remark=?, private_key_content=?, password=?
        WHERE id=?
    ''', (name, ip, port, username, group_id, remark, private_key_content, password, server_id))
    conn.commit()
    conn.close()

def delete_server(server_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE servers SET is_deleted = 1 WHERE id = ?', (server_id,))
    cursor.execute('UPDATE inspection_records SET is_deleted = 1 WHERE server_id = ?', (server_id,))
    conn.commit()
    conn.close()

def add_inspection_record(server_id, disk_usage, memory_usage, cpu_usage, system_time, os_version, alert_content, report_content, inspection_result=None, inspection_time=None):
    conn = get_connection()
    cursor = conn.cursor()
    if inspection_time:
        cursor.execute('''
            INSERT INTO inspection_records (server_id, disk_usage, memory_usage, cpu_usage, system_time, os_version, alert_content, report_content, inspection_result, inspection_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (server_id, disk_usage, memory_usage, cpu_usage, system_time, os_version, alert_content, report_content, inspection_result, inspection_time))
    else:
        cursor.execute('''
            INSERT INTO inspection_records (server_id, disk_usage, memory_usage, cpu_usage, system_time, os_version, alert_content, report_content, inspection_result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (server_id, disk_usage, memory_usage, cpu_usage, system_time, os_version, alert_content, report_content, inspection_result))
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return record_id

def get_inspection_records(server_id=None, group_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if server_id:
        cursor.execute('''
            SELECT ir.*, s.name as server_name, s.ip as server_ip, g.name as group_name 
            FROM inspection_records ir 
            LEFT JOIN servers s ON ir.server_id = s.id
            LEFT JOIN groups g ON s.group_id = g.id
            WHERE ir.server_id = ? AND ir.is_deleted = 0 ORDER BY ir.inspection_time DESC
        ''', (server_id,))
    elif group_id and group_id != 'all':
        cursor.execute('''
            SELECT ir.*, s.name as server_name, s.ip as server_ip, g.name as group_name 
            FROM inspection_records ir 
            LEFT JOIN servers s ON ir.server_id = s.id
            LEFT JOIN groups g ON s.group_id = g.id
            WHERE s.group_id = ? AND ir.is_deleted = 0 ORDER BY ir.inspection_time DESC
        ''', (group_id,))
    else:
        cursor.execute('''
            SELECT ir.*, s.name as server_name, s.ip as server_ip, g.name as group_name 
            FROM inspection_records ir 
            LEFT JOIN servers s ON ir.server_id = s.id
            LEFT JOIN groups g ON s.group_id = g.id
            WHERE ir.is_deleted = 0 ORDER BY ir.inspection_time DESC
        ''')
    records = cursor.fetchall()
    conn.close()
    return records

def get_inspection_record_by_id(record_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM inspection_records WHERE id = ? AND is_deleted = 0', (record_id,))
    record = cursor.fetchone()
    conn.close()
    return record

def search_servers(ip):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.id, s.name, s.ip, s.port, s.username, s.group_id, g.name as group_name, s.remark, s.created_at 
        FROM servers s LEFT JOIN groups g ON s.group_id = g.id 
        WHERE s.ip LIKE ? ORDER BY s.created_at DESC
    ''', ('%' + ip + '%',))
    servers = cursor.fetchall()
    conn.close()
    return servers

# 定时任务相关函数
def add_scheduled_task(server_id, cron_expression, is_enabled=1):
    conn = get_connection()
    cursor = conn.cursor()
    # 先将该服务器的现有任务标记为删除
    cursor.execute('UPDATE scheduled_tasks SET is_deleted = 1 WHERE server_id = ? AND is_deleted = 0', (server_id,))
    # 添加新任务
    cursor.execute('''
        INSERT INTO scheduled_tasks (server_id, cron_expression, is_enabled)
        VALUES (?, ?, ?)
    ''', (server_id, cron_expression, is_enabled))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return task_id

def get_scheduled_task_by_server_id(server_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM scheduled_tasks WHERE server_id = ? AND is_deleted = 0', (server_id,))
    task = cursor.fetchone()
    conn.close()
    return task

def get_all_scheduled_tasks():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT st.*, s.name as server_name, s.ip as server_ip, g.name as group_name
        FROM scheduled_tasks st
        LEFT JOIN servers s ON st.server_id = s.id
        LEFT JOIN groups g ON s.group_id = g.id
        WHERE st.is_deleted = 0
        ORDER BY st.is_enabled DESC, st.cron_expression
    ''')
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def update_scheduled_task(task_id, cron_expression, is_enabled):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE scheduled_tasks SET cron_expression = ?, is_enabled = ?
        WHERE id = ? AND is_deleted = 0
    ''', (cron_expression, is_enabled, task_id))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def delete_scheduled_task(server_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE scheduled_tasks SET is_deleted = 1 WHERE server_id = ? AND is_deleted = 0', (server_id,))
    conn.commit()
    conn.close()

# 报告相关函数
def add_report(report_type, group_id, group_name, report_name):
    conn = get_connection()
    cursor = conn.cursor()
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO reports (report_type, group_id, group_name, report_name, generated_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (report_type, group_id, group_name, report_name, generated_at))
    conn.commit()
    report_id = cursor.lastrowid
    conn.close()
    return report_id

def get_all_reports(filter_type=None, filter_group=None, filter_date=None):
    conn = get_connection()
    cursor = conn.cursor()
    query = '''
        SELECT * FROM reports
        WHERE 1=1 AND is_deleted = 0
    '''
    params = []
    
    if filter_type:
        query += ' AND report_type = ?'
        params.append(filter_type)
    
    if filter_group:
        query += ' AND group_id = ?'
        params.append(filter_group)
    
    if filter_date:
        query += ' AND DATE(generated_at) = ?'
        params.append(filter_date)
    
    query += ' ORDER BY generated_at DESC'
    
    cursor.execute(query, params)
    reports = cursor.fetchall()
    conn.close()
    return reports

def delete_report(report_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE reports SET is_deleted = 1 WHERE id = ? AND is_deleted = 0', (report_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

# 更新分组排序
def update_group_sort_order(group_id, sort_order):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE groups SET sort_order = ? WHERE id = ?', (sort_order, group_id))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

init_db()