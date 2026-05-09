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
            file_path TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            FOREIGN KEY (group_id) REFERENCES groups(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inspection_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            command TEXT NOT NULL,
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            is_enabled INTEGER DEFAULT 1,
            is_deleted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('SELECT COUNT(*) FROM groups')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO groups (name) VALUES (?)', ('默认分组',))
    
    cursor.execute('SELECT COUNT(*) FROM inspection_items')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO inspection_items (name, command, description, sort_order) VALUES (?, ?, ?, ?)', ('CPU使用率', "top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'", '获取CPU使用率', 1))
        cursor.execute('INSERT INTO inspection_items (name, command, description, sort_order) VALUES (?, ?, ?, ?)', ('内存使用情况', 'free -h', '获取内存使用情况', 2))
        cursor.execute('INSERT INTO inspection_items (name, command, description, sort_order) VALUES (?, ?, ?, ?)', ('磁盘使用情况', 'df -h', '获取磁盘使用情况', 3))
        cursor.execute('INSERT INTO inspection_items (name, command, description, sort_order) VALUES (?, ?, ?, ?)', ('系统时间', 'date "+%Y-%m-%d %H:%M:%S"', '获取系统时间', 4))
        cursor.execute('INSERT INTO inspection_items (name, command, description, sort_order) VALUES (?, ?, ?, ?)', ('操作系统版本', 'cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null || uname -a', '获取操作系统版本', 5))
    
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

def get_all_servers(group_id=None, page=1, per_page=10):
    conn = get_connection()
    cursor = conn.cursor()
    offset = (page - 1) * per_page
    if group_id and group_id != 'all':
        cursor.execute('''
            SELECT s.id, s.name, s.ip, s.port, s.username, s.group_id, g.name as group_name, s.remark, s.created_at 
            FROM servers s LEFT JOIN groups g ON s.group_id = g.id 
            WHERE s.group_id = ? AND s.is_deleted = 0 ORDER BY s.created_at DESC LIMIT ? OFFSET ?
        ''', (group_id, per_page, offset))
    else:
        cursor.execute('''
            SELECT s.id, s.name, s.ip, s.port, s.username, s.group_id, g.name as group_name, s.remark, s.created_at 
            FROM servers s LEFT JOIN groups g ON s.group_id = g.id 
            WHERE s.is_deleted = 0 ORDER BY s.created_at DESC LIMIT ? OFFSET ?
        ''', (per_page, offset))
    servers = cursor.fetchall()
    conn.close()
    return servers

def get_servers_count(group_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if group_id and group_id != 'all':
        cursor.execute('SELECT COUNT(*) FROM servers WHERE group_id = ? AND is_deleted = 0', (group_id,))
    else:
        cursor.execute('SELECT COUNT(*) FROM servers WHERE is_deleted = 0')
    count = cursor.fetchone()[0]
    conn.close()
    return count

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

def get_inspection_records(server_id=None, group_id=None, page=1, per_page=10):
    conn = get_connection()
    cursor = conn.cursor()
    offset = (page - 1) * per_page
    if server_id:
        cursor.execute('''
            SELECT ir.*, s.name as server_name, s.ip as server_ip, g.name as group_name 
            FROM inspection_records ir 
            LEFT JOIN servers s ON ir.server_id = s.id
            LEFT JOIN groups g ON s.group_id = g.id
            WHERE ir.server_id = ? AND ir.is_deleted = 0 ORDER BY ir.inspection_time DESC LIMIT ? OFFSET ?
        ''', (server_id, per_page, offset))
    elif group_id and group_id != 'all':
        cursor.execute('''
            SELECT ir.*, s.name as server_name, s.ip as server_ip, g.name as group_name 
            FROM inspection_records ir 
            LEFT JOIN servers s ON ir.server_id = s.id
            LEFT JOIN groups g ON s.group_id = g.id
            WHERE s.group_id = ? AND ir.is_deleted = 0 ORDER BY ir.inspection_time DESC LIMIT ? OFFSET ?
        ''', (group_id, per_page, offset))
    else:
        cursor.execute('''
            SELECT ir.*, s.name as server_name, s.ip as server_ip, g.name as group_name 
            FROM inspection_records ir 
            LEFT JOIN servers s ON ir.server_id = s.id
            LEFT JOIN groups g ON s.group_id = g.id
            WHERE ir.is_deleted = 0 ORDER BY ir.inspection_time DESC LIMIT ? OFFSET ?
        ''', (per_page, offset))
    records = cursor.fetchall()
    conn.close()
    return records

def get_inspection_records_count(server_id=None, group_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if server_id:
        cursor.execute('SELECT COUNT(*) FROM inspection_records WHERE server_id = ? AND is_deleted = 0', (server_id,))
    elif group_id and group_id != 'all':
        cursor.execute('''
            SELECT COUNT(*) FROM inspection_records ir 
            LEFT JOIN servers s ON ir.server_id = s.id
            WHERE s.group_id = ? AND ir.is_deleted = 0
        ''', (group_id,))
    else:
        cursor.execute('SELECT COUNT(*) FROM inspection_records WHERE is_deleted = 0')
    count = cursor.fetchone()[0]
    conn.close()
    return count

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

def get_all_scheduled_tasks(page=1, per_page=10):
    conn = get_connection()
    cursor = conn.cursor()
    offset = (page - 1) * per_page
    cursor.execute('''
        SELECT st.*, s.name as server_name, s.ip as server_ip, g.name as group_name
        FROM scheduled_tasks st
        LEFT JOIN servers s ON st.server_id = s.id
        LEFT JOIN groups g ON s.group_id = g.id
        WHERE st.is_deleted = 0
        ORDER BY st.is_enabled DESC, st.cron_expression LIMIT ? OFFSET ?
    ''', (per_page, offset))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def get_scheduled_tasks_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM scheduled_tasks WHERE is_deleted = 0')
    count = cursor.fetchone()[0]
    conn.close()
    return count

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
def add_report(report_type, group_id, group_name, report_name, file_path=None):
    conn = get_connection()
    cursor = conn.cursor()
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO reports (report_type, group_id, group_name, report_name, file_path, generated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (report_type, group_id, group_name, report_name, file_path, generated_at))
    conn.commit()
    report_id = cursor.lastrowid
    conn.close()
    return report_id

def get_all_reports(filter_type=None, filter_group=None, filter_date=None, page=1, per_page=10):
    conn = get_connection()
    cursor = conn.cursor()
    offset = (page - 1) * per_page
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
    
    query += ' ORDER BY generated_at DESC LIMIT ? OFFSET ?'
    params.extend([per_page, offset])
    
    cursor.execute(query, params)
    reports = cursor.fetchall()
    conn.close()
    return reports

def get_reports_count(filter_type=None, filter_group=None, filter_date=None):
    conn = get_connection()
    cursor = conn.cursor()
    query = '''
        SELECT COUNT(*) FROM reports
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
    
    cursor.execute(query, params)
    count = cursor.fetchone()[0]
    conn.close()
    return count

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

# 巡检项相关操作

def add_inspection_item(name, command, description=''):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO inspection_items (name, command, description)
        VALUES (?, ?, ?)
    ''', (name, command, description))
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()
    return item_id

def get_all_inspection_items():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, command, description, sort_order, is_enabled FROM inspection_items WHERE is_deleted = 0 ORDER BY sort_order ASC')
    items = cursor.fetchall()
    conn.close()
    return items

def get_inspection_item_by_id(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, command, description, sort_order, is_enabled FROM inspection_items WHERE id = ? AND is_deleted = 0', (item_id,))
    item = cursor.fetchone()
    conn.close()
    return item

def update_inspection_item(item_id, name, command, description=''):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE inspection_items SET name = ?, command = ?, description = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND is_deleted = 0
    ''', (name, command, description, item_id))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def delete_inspection_item(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE inspection_items SET is_deleted = 1 WHERE id = ? AND is_deleted = 0', (item_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def toggle_inspection_item(item_id, is_enabled):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE inspection_items SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND is_deleted = 0', (is_enabled, item_id))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def update_inspection_item_sort_order(item_id, sort_order):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE inspection_items SET sort_order = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (sort_order, item_id))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

init_db()