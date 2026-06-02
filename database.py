from datetime import datetime
from config import (
    DATABASE_TYPE,
    DATABASE_PATH,
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_PASSWORD,
    DB_DATABASE
)
from encryption import encrypt_password, decrypt_password

# 全局连接对象
_conn = None

def _get_db_module():
    """根据数据库类型返回对应的数据库模块"""
    if DATABASE_TYPE == 'postgresql':
        import psycopg
        return psycopg
    elif DATABASE_TYPE != 'sqlite':
        import mysql.connector
        return mysql.connector
    else:  # sqlite
        import sqlite3
        return sqlite3

def _get_connection_string():
    """获取数据库连接字符串/参数"""
    if DATABASE_TYPE == 'postgresql':
        return {
            'host': DB_HOST,
            'port': DB_PORT,
            'user': DB_USER,
            'password': DB_PASSWORD,
            'database': DB_DATABASE
        }
    elif DATABASE_TYPE != 'sqlite':
        return {
            'host': DB_HOST,
            'port': DB_PORT,
            'user': DB_USER,
            'password': DB_PASSWORD,
            'database': DB_DATABASE,
            'charset': 'utf8mb4'
        }
    else:  # sqlite
        return DATABASE_PATH

def get_connection():
    """获取数据库连接"""
    db_module = _get_db_module()
    conn_params = _get_connection_string()
    
    if DATABASE_TYPE == 'sqlite':
        conn = db_module.connect(conn_params)
        conn.execute('PRAGMA foreign_keys = ON')
    elif DATABASE_TYPE == 'postgresql':
        # psycopg3 使用 url 或 conninfo 连接
        conninfo = f"host={conn_params['host']} port={conn_params['port']} dbname={conn_params['database']} user={conn_params['user']} password={conn_params['password']}"
        conn = db_module.connect(conninfo)
    elif DATABASE_TYPE != 'sqlite':
        conn = db_module.connect(**conn_params)
    
    # 设置连接属性
    if DATABASE_TYPE == 'postgresql':
        conn.autocommit = False
    elif DATABASE_TYPE != 'sqlite':
        conn.autocommit = False
    
    return conn

def _get_primary_key_syntax():
    """获取主键自增语法"""
    if DATABASE_TYPE == 'postgresql':
        return 'SERIAL PRIMARY KEY'
    elif DATABASE_TYPE != 'sqlite':
        return 'INT PRIMARY KEY AUTO_INCREMENT'
    else:  # sqlite
        return 'INTEGER PRIMARY KEY AUTOINCREMENT'

def _get_timestamp_syntax():
    """获取时间戳语法"""
    if DATABASE_TYPE == 'postgresql':
        return 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
    elif DATABASE_TYPE != 'sqlite':
        return 'DATETIME DEFAULT CURRENT_TIMESTAMP'
    else:  # sqlite
        return 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'

def _get_blob_type():
    """获取BLOB类型"""
    if DATABASE_TYPE == 'postgresql':
        return 'BYTEA'
    elif DATABASE_TYPE != 'sqlite':
        return 'LONGBLOB'
    else:  # sqlite
        return 'BLOB'

def _get_limit_offset_syntax(query, limit, offset):
    """获取分页语法"""
    if DATABASE_TYPE != 'sqlite':
        return f"{query} LIMIT {limit} OFFSET {offset}"
    else:  # sqlite, postgresql
        return f"{query} LIMIT ? OFFSET ?"

def _get_placeholder():
    """获取参数占位符"""
    if DATABASE_TYPE == 'sqlite':
        return '?'
    else:  # postgresql, mysql 都使用 %s
        return '%s'

def _execute_query(cursor, query, params=None):
    """执行查询，处理不同数据库的参数格式"""
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 用户表
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS users (
            id {_get_primary_key_syntax()},
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at {_get_timestamp_syntax()}
        )
    ''')
    
    # 检查是否存在默认管理员用户
    cursor.execute('SELECT id FROM users WHERE username = %s' if DATABASE_TYPE != 'sqlite' else 'SELECT id FROM users WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (username, password)
            VALUES (%s, %s)
        ''' if DATABASE_TYPE != 'sqlite' else '''
            INSERT INTO users (username, password)
            VALUES (?, ?)
        ''', ('admin', encrypt_password('admin123')))
    
    # 分组表
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS groups (
            id {_get_primary_key_syntax()},
            name TEXT NOT NULL UNIQUE,
            parent_id INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            parent_id INTEGER DEFAULT NULL,
            is_deleted INTEGER DEFAULT 0,
            created_at {_get_timestamp_syntax()}
        )
    ''')
    
    # 服务器表
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS servers (
            id {_get_primary_key_syntax()},
            name TEXT NOT NULL,
            ip TEXT NOT NULL,
            port INTEGER DEFAULT 22,
            username TEXT NOT NULL,
            private_key_content {_get_blob_type()},
            password TEXT,
            group_id INTEGER DEFAULT 1,
            remark TEXT,
            os_type TEXT DEFAULT 'linux',
            is_deleted INTEGER DEFAULT 0,
            created_at {_get_timestamp_syntax()}
        )
    ''')
    
    # 巡检记录表
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS inspection_records (
            id {_get_primary_key_syntax()},
            server_id INTEGER,
            disk_usage TEXT,
            memory_usage TEXT,
            cpu_usage TEXT,
            system_time TEXT,
            os_version TEXT,
            inspection_time {_get_timestamp_syntax()},
            alert_content TEXT,
            report_content TEXT,
            inspection_result TEXT,
            is_deleted INTEGER DEFAULT 0
        )
    ''')
    
    # 定时任务表
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id {_get_primary_key_syntax()},
            server_id INTEGER,
            cron_expression TEXT,
            is_enabled INTEGER DEFAULT 1,
            is_deleted INTEGER DEFAULT 0,
            created_at {_get_timestamp_syntax()}
        )
    ''')
    
    # 报告表
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS reports (
            id {_get_primary_key_syntax()},
            report_type TEXT,
            group_id INTEGER,
            group_name TEXT,
            report_name TEXT,
            file_path TEXT,
            generated_at {_get_timestamp_syntax()},
            is_deleted INTEGER DEFAULT 0
        )
    ''')
    
    # 巡检项表
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS inspection_items (
            id {_get_primary_key_syntax()},
            name TEXT NOT NULL,
            command TEXT NOT NULL,
            description TEXT,
            os_type TEXT DEFAULT 'linux',
            sort_order INTEGER DEFAULT 0,
            is_enabled INTEGER DEFAULT 1,
            is_deleted INTEGER DEFAULT 0,
            created_at {_get_timestamp_syntax()},
            updated_at {_get_timestamp_syntax()}
        )
    ''')
    
    # 文件上传记录表
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS upload_records (
            id {_get_primary_key_syntax()},
            file_name TEXT NOT NULL,
            original_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            storage_type TEXT DEFAULT 'local',
            storage_time {_get_timestamp_syntax()},
            is_deleted INTEGER DEFAULT 0,
            created_at {_get_timestamp_syntax()}
        )
    ''')
    
    # 故障处置表
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS faults (
            id {_get_primary_key_syntax()},
            group_id INTEGER,
            group_name TEXT,
            event_name TEXT NOT NULL,
            fault_level TEXT,
            fault_type TEXT,
            fault_description TEXT,
            occurrence_time {_get_timestamp_syntax()},
            discoverer TEXT,
            processing_status TEXT DEFAULT '待处理',
            processing_person TEXT,
            processing_time {_get_timestamp_syntax()},
            processing_description TEXT,
            review_status TEXT DEFAULT '待审核',
            review_person TEXT,
            review_time {_get_timestamp_syntax()},
            review_comment TEXT,
            report_path TEXT,
            is_deleted INTEGER DEFAULT 0,
            created_at {_get_timestamp_syntax()},
            updated_at {_get_timestamp_syntax()}
        )
    ''')
    
    # 检查默认分组
    cursor.execute('SELECT COUNT(*) FROM groups')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO groups (name) VALUES (%s)' if DATABASE_TYPE != 'sqlite' else 'INSERT INTO groups (name) VALUES (?)', ('默认分组',))
    
    # 检查默认巡检项
    cursor.execute('SELECT COUNT(*) FROM inspection_items')
    if cursor.fetchone()[0] == 0:
        items = [
            ('CPU使用率', "top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'", '获取CPU使用率', 1),
            ('内存使用情况', 'free -h', '获取内存使用情况', 2),
            ('磁盘使用情况', 'df -h', '获取磁盘使用情况', 3),
            ('系统时间', 'date "+%Y-%m-%d %H:%M:%S"', '获取系统时间', 4),
            ('操作系统版本', 'cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null || uname -a', '获取操作系统版本', 5)
        ]
        for item in items:
            cursor.execute('''
                INSERT INTO inspection_items (name, command, description, sort_order) 
                VALUES (%s, %s, %s, %s)
            ''' if DATABASE_TYPE != 'sqlite' else '''
                INSERT INTO inspection_items (name, command, description, sort_order) 
                VALUES (?, ?, ?, ?)
            ''', item)
    
    # 告警通知配置表
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS alert_configs (
            id {_get_primary_key_syntax()},
            provider TEXT NOT NULL,
            is_enabled INTEGER DEFAULT 1,
            access_key_id TEXT,
            access_key_secret TEXT,
            secret_id TEXT,
            secret_key TEXT,
            sign_name TEXT NOT NULL,
            app_id TEXT,
            inspection_template_code TEXT,
            fault_template_code TEXT,
            system_template_code TEXT,
            phone_numbers TEXT NOT NULL,
            custom_api_url TEXT,
            custom_headers TEXT,
            created_at {_get_timestamp_syntax()},
            updated_at {_get_timestamp_syntax()}
        )
    ''')
    
    # 告警记录表
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS alert_logs (
            id {_get_primary_key_syntax()},
            alert_type TEXT NOT NULL,
            alert_title TEXT NOT NULL,
            alert_content TEXT,
            phone_numbers TEXT NOT NULL,
            send_status TEXT NOT NULL,
            send_result TEXT,
            created_at {_get_timestamp_syntax()}
        )
    ''')
    
    conn.commit()
    conn.close()

def add_group(name, sort_order=0, parent_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO groups (name, sort_order, parent_id) VALUES (%s, %s, %s)' if DATABASE_TYPE != 'sqlite' else 'INSERT INTO groups (name, sort_order, parent_id) VALUES (?, ?, ?)', (name, sort_order, parent_id))
        conn.commit()
        group_id = cursor.lastrowid
        conn.close()
        return group_id
    except Exception as e:
        conn.close()
        return None

def get_all_groups():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, sort_order, parent_id FROM groups WHERE is_deleted = 0 ORDER BY sort_order ASC, created_at DESC')
    groups = cursor.fetchall()
    conn.close()
    return groups

def get_group_by_id(group_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM groups WHERE id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'SELECT * FROM groups WHERE id = ? AND is_deleted = 0', (group_id,))
    group = cursor.fetchone()
    conn.close()
    return group

def delete_group(group_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE servers SET group_id = 1 WHERE group_id = %s' if DATABASE_TYPE != 'sqlite' else 'UPDATE servers SET group_id = 1 WHERE group_id = ?', (group_id,))
    cursor.execute('UPDATE groups SET is_deleted = 1 WHERE id = %s' if DATABASE_TYPE != 'sqlite' else 'UPDATE groups SET is_deleted = 1 WHERE id = ?', (group_id,))
    conn.commit()
    conn.close()

def update_group(group_id, name=None, sort_order=None, parent_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        updates = []
        params = []
        
        if name is not None:
            updates.append('name = %s' if DATABASE_TYPE != 'sqlite' else 'name = ?')
            params.append(name)
        if sort_order is not None:
            updates.append('sort_order = %s' if DATABASE_TYPE != 'sqlite' else 'sort_order = ?')
            params.append(sort_order)
        if parent_id is not None:
            updates.append('parent_id = %s' if DATABASE_TYPE != 'sqlite' else 'parent_id = ?')
            params.append(parent_id)
        
        if not updates:
            conn.close()
            return False
        
        params.append(group_id)
        cursor.execute('UPDATE groups SET ' + ', '.join(updates) + ' WHERE id = %s' if DATABASE_TYPE != 'sqlite' else 'UPDATE groups SET ' + ', '.join(updates) + ' WHERE id = ?', params)
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        return rows_affected > 0
    except Exception as e:
        conn.close()
        return None

def add_server(name, ip, port, username, group_id=1, remark='', private_key_content=None, password=None, os_type='linux'):
    conn = get_connection()
    cursor = conn.cursor()
    encrypted_password = encrypt_password(password)
    cursor.execute('''
        INSERT INTO servers (name, ip, port, username, group_id, remark, private_key_content, password, os_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''' if DATABASE_TYPE != 'sqlite' else '''
        INSERT INTO servers (name, ip, port, username, group_id, remark, private_key_content, password, os_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, ip, port, username, group_id, remark, private_key_content, encrypted_password, os_type))
    conn.commit()
    server_id = cursor.lastrowid
    conn.close()
    return server_id

def get_all_servers(group_id=None, page=1, per_page=10):
    conn = get_connection()
    cursor = conn.cursor()
    offset = (page - 1) * per_page
    
    if group_id and group_id != 'all':
        query = '''
            SELECT s.id, s.name, s.ip, s.port, s.username, s.group_id, g.name as group_name, s.remark, s.os_type, s.created_at 
            FROM servers s LEFT JOIN groups g ON s.group_id = g.id 
            WHERE s.group_id = %s AND s.is_deleted = 0 ORDER BY s.created_at DESC
        ''' if DATABASE_TYPE != 'sqlite' else '''
            SELECT s.id, s.name, s.ip, s.port, s.username, s.group_id, g.name as group_name, s.remark, s.os_type, s.created_at 
            FROM servers s LEFT JOIN groups g ON s.group_id = g.id 
            WHERE s.group_id = ? AND s.is_deleted = 0 ORDER BY s.created_at DESC
        '''
        if DATABASE_TYPE != 'sqlite':
            query += f' LIMIT {per_page} OFFSET {offset}'
            cursor.execute(query, (group_id,))
        else:
            query += ' LIMIT ? OFFSET ?'
            cursor.execute(query, (group_id, per_page, offset))
    else:
        query = '''
            SELECT s.id, s.name, s.ip, s.port, s.username, s.group_id, g.name as group_name, s.remark, s.os_type, s.created_at 
            FROM servers s LEFT JOIN groups g ON s.group_id = g.id 
            WHERE s.is_deleted = 0 ORDER BY s.created_at DESC
        '''
        if DATABASE_TYPE != 'sqlite':
            query += f' LIMIT {per_page} OFFSET {offset}'
            cursor.execute(query)
        else:
            query += ' LIMIT ? OFFSET ?'
            cursor.execute(query, (per_page, offset))
    
    servers = cursor.fetchall()
    conn.close()
    return servers

def get_servers_count(group_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if group_id and group_id != 'all':
        cursor.execute('SELECT COUNT(*) FROM servers WHERE group_id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'SELECT COUNT(*) FROM servers WHERE group_id = ? AND is_deleted = 0', (group_id,))
    else:
        cursor.execute('SELECT COUNT(*) FROM servers WHERE is_deleted = 0')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_server_by_id(server_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM servers WHERE id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'SELECT * FROM servers WHERE id = ? AND is_deleted = 0', (server_id,))
    server = cursor.fetchone()
    conn.close()
    
    if server:
        server_list = list(server)
        if server_list[6]:
            server_list[6] = decrypt_password(server_list[6])
        server = tuple(server_list)
    
    return server

def update_server(server_id, name, ip, port, username, group_id=1, remark='', private_key_content=None, password=None, os_type='linux'):
    conn = get_connection()
    cursor = conn.cursor()
    encrypted_password = encrypt_password(password)
    cursor.execute('''
        UPDATE servers SET name=%s, ip=%s, port=%s, username=%s, group_id=%s, remark=%s, private_key_content=%s, password=%s, os_type=%s
        WHERE id=%s
    ''' if DATABASE_TYPE != 'sqlite' else '''
        UPDATE servers SET name=?, ip=?, port=?, username=?, group_id=?, remark=?, private_key_content=?, password=?, os_type=?
        WHERE id=?
    ''', (name, ip, port, username, group_id, remark, private_key_content, encrypted_password, os_type, server_id))
    conn.commit()
    conn.close()

def delete_server(server_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE servers SET is_deleted = 1 WHERE id = %s' if DATABASE_TYPE != 'sqlite' else 'UPDATE servers SET is_deleted = 1 WHERE id = ?', (server_id,))
    cursor.execute('UPDATE inspection_records SET is_deleted = 1 WHERE server_id = %s' if DATABASE_TYPE != 'sqlite' else 'UPDATE inspection_records SET is_deleted = 1 WHERE server_id = ?', (server_id,))
    conn.commit()
    conn.close()

def add_inspection_record(server_id, disk_usage, memory_usage, cpu_usage, system_time, os_version, alert_content, report_content, inspection_result=None, inspection_time=None):
    conn = get_connection()
    cursor = conn.cursor()
    if inspection_time:
        cursor.execute('''
            INSERT INTO inspection_records (server_id, disk_usage, memory_usage, cpu_usage, system_time, os_version, alert_content, report_content, inspection_result, inspection_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''' if DATABASE_TYPE != 'sqlite' else '''
            INSERT INTO inspection_records (server_id, disk_usage, memory_usage, cpu_usage, system_time, os_version, alert_content, report_content, inspection_result, inspection_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (server_id, disk_usage, memory_usage, cpu_usage, system_time, os_version, alert_content, report_content, inspection_result, inspection_time))
    else:
        cursor.execute('''
            INSERT INTO inspection_records (server_id, disk_usage, memory_usage, cpu_usage, system_time, os_version, alert_content, report_content, inspection_result)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''' if DATABASE_TYPE != 'sqlite' else '''
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
        query = '''
            SELECT ir.*, s.name as server_name, s.ip as server_ip, g.name as group_name 
            FROM inspection_records ir 
            LEFT JOIN servers s ON ir.server_id = s.id
            LEFT JOIN groups g ON s.group_id = g.id
            WHERE ir.server_id = %s AND ir.is_deleted = 0 ORDER BY ir.inspection_time DESC
        ''' if DATABASE_TYPE != 'sqlite' else '''
            SELECT ir.*, s.name as server_name, s.ip as server_ip, g.name as group_name 
            FROM inspection_records ir 
            LEFT JOIN servers s ON ir.server_id = s.id
            LEFT JOIN groups g ON s.group_id = g.id
            WHERE ir.server_id = ? AND ir.is_deleted = 0 ORDER BY ir.inspection_time DESC
        '''
        if DATABASE_TYPE != 'sqlite':
            query += f' LIMIT {per_page} OFFSET {offset}'
            cursor.execute(query, (server_id,))
        else:
            query += ' LIMIT ? OFFSET ?'
            cursor.execute(query, (server_id, per_page, offset))
    elif group_id and group_id != 'all':
        query = '''
            SELECT ir.*, s.name as server_name, s.ip as server_ip, g.name as group_name 
            FROM inspection_records ir 
            LEFT JOIN servers s ON ir.server_id = s.id
            LEFT JOIN groups g ON s.group_id = g.id
            WHERE s.group_id = %s AND ir.is_deleted = 0 ORDER BY ir.inspection_time DESC
        ''' if DATABASE_TYPE != 'sqlite' else '''
            SELECT ir.*, s.name as server_name, s.ip as server_ip, g.name as group_name 
            FROM inspection_records ir 
            LEFT JOIN servers s ON ir.server_id = s.id
            LEFT JOIN groups g ON s.group_id = g.id
            WHERE s.group_id = ? AND ir.is_deleted = 0 ORDER BY ir.inspection_time DESC
        '''
        if DATABASE_TYPE != 'sqlite':
            query += f' LIMIT {per_page} OFFSET {offset}'
            cursor.execute(query, (group_id,))
        else:
            query += ' LIMIT ? OFFSET ?'
            cursor.execute(query, (group_id, per_page, offset))
    else:
        query = '''
            SELECT ir.*, s.name as server_name, s.ip as server_ip, g.name as group_name 
            FROM inspection_records ir 
            LEFT JOIN servers s ON ir.server_id = s.id
            LEFT JOIN groups g ON s.group_id = g.id
            WHERE ir.is_deleted = 0 ORDER BY ir.inspection_time DESC
        '''
        if DATABASE_TYPE != 'sqlite':
            query += f' LIMIT {per_page} OFFSET {offset}'
            cursor.execute(query)
        else:
            query += ' LIMIT ? OFFSET ?'
            cursor.execute(query, (per_page, offset))
    
    records = cursor.fetchall()
    conn.close()
    return records

def get_inspection_records_count(server_id=None, group_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if server_id:
        cursor.execute('SELECT COUNT(*) FROM inspection_records WHERE server_id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'SELECT COUNT(*) FROM inspection_records WHERE server_id = ? AND is_deleted = 0', (server_id,))
    elif group_id and group_id != 'all':
        cursor.execute('''
            SELECT COUNT(*) FROM inspection_records ir 
            LEFT JOIN servers s ON ir.server_id = s.id
            WHERE s.group_id = %s AND ir.is_deleted = 0
        ''' if DATABASE_TYPE != 'sqlite' else '''
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
    cursor.execute('SELECT * FROM inspection_records WHERE id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'SELECT * FROM inspection_records WHERE id = ? AND is_deleted = 0', (record_id,))
    record = cursor.fetchone()
    conn.close()
    return record

def search_servers(ip):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.id, s.name, s.ip, s.port, s.username, s.group_id, g.name as group_name, s.remark, s.created_at 
        FROM servers s LEFT JOIN groups g ON s.group_id = g.id 
        WHERE s.ip LIKE %s ORDER BY s.created_at DESC
    ''' if DATABASE_TYPE != 'sqlite' else '''
        SELECT s.id, s.name, s.ip, s.port, s.username, s.group_id, g.name as group_name, s.remark, s.created_at 
        FROM servers s LEFT JOIN groups g ON s.group_id = g.id 
        WHERE s.ip LIKE ? ORDER BY s.created_at DESC
    ''', ('%' + ip + '%',))
    servers = cursor.fetchall()
    conn.close()
    return servers

def add_scheduled_task(server_id, cron_expression, is_enabled=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE scheduled_tasks SET is_deleted = 1 WHERE server_id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'UPDATE scheduled_tasks SET is_deleted = 1 WHERE server_id = ? AND is_deleted = 0', (server_id,))
    cursor.execute('''
        INSERT INTO scheduled_tasks (server_id, cron_expression, is_enabled)
        VALUES (%s, %s, %s)
    ''' if DATABASE_TYPE != 'sqlite' else '''
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
    cursor.execute('SELECT * FROM scheduled_tasks WHERE server_id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'SELECT * FROM scheduled_tasks WHERE server_id = ? AND is_deleted = 0', (server_id,))
    task = cursor.fetchone()
    conn.close()
    return task

def get_all_scheduled_tasks(page=1, per_page=10):
    conn = get_connection()
    cursor = conn.cursor()
    offset = (page - 1) * per_page
    
    query = '''
        SELECT st.*, s.name as server_name, s.ip as server_ip, g.name as group_name
        FROM scheduled_tasks st
        LEFT JOIN servers s ON st.server_id = s.id
        LEFT JOIN groups g ON s.group_id = g.id
        WHERE st.is_deleted = 0
        ORDER BY st.is_enabled DESC, st.cron_expression
    '''
    if DATABASE_TYPE != 'sqlite':
        query += f' LIMIT {per_page} OFFSET {offset}'
        cursor.execute(query)
    else:
        query += ' LIMIT ? OFFSET ?'
        cursor.execute(query, (per_page, offset))
    
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
        UPDATE scheduled_tasks SET cron_expression = %s, is_enabled = %s
        WHERE id = %s AND is_deleted = 0
    ''' if DATABASE_TYPE != 'sqlite' else '''
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
    cursor.execute('UPDATE scheduled_tasks SET is_deleted = 1 WHERE server_id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'UPDATE scheduled_tasks SET is_deleted = 1 WHERE server_id = ? AND is_deleted = 0', (server_id,))
    conn.commit()
    conn.close()

def add_report(report_type, group_id, group_name, report_name, file_path=None):
    conn = get_connection()
    cursor = conn.cursor()
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO reports (report_type, group_id, group_name, report_name, file_path, generated_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''' if DATABASE_TYPE != 'sqlite' else '''
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
        query += ' AND report_type = %s' if DATABASE_TYPE != 'sqlite' else ' AND report_type = ?'
        params.append(filter_type)
    
    if filter_group:
        query += ' AND group_id = %s' if DATABASE_TYPE != 'sqlite' else ' AND group_id = ?'
        params.append(filter_group)
    
    if filter_date:
        query += ' AND DATE(generated_at) = %s' if DATABASE_TYPE != 'sqlite' else ' AND DATE(generated_at) = ?'
        params.append(filter_date)
    
    query += ' ORDER BY generated_at DESC'
    
    if DATABASE_TYPE != 'sqlite':
        query += f' LIMIT {per_page} OFFSET {offset}'
        cursor.execute(query, tuple(params))
    else:
        query += ' LIMIT ? OFFSET ?'
        params.extend([per_page, offset])
        cursor.execute(query, tuple(params))
    
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
        query += ' AND report_type = %s' if DATABASE_TYPE != 'sqlite' else ' AND report_type = ?'
        params.append(filter_type)
    
    if filter_group:
        query += ' AND group_id = %s' if DATABASE_TYPE != 'sqlite' else ' AND group_id = ?'
        params.append(filter_group)
    
    if filter_date:
        query += ' AND DATE(generated_at) = %s' if DATABASE_TYPE != 'sqlite' else ' AND DATE(generated_at) = ?'
        params.append(filter_date)
    
    cursor.execute(query, tuple(params))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def delete_report(report_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE reports SET is_deleted = 1 WHERE id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'UPDATE reports SET is_deleted = 1 WHERE id = ? AND is_deleted = 0', (report_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def update_group_sort_order(group_id, sort_order):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE groups SET sort_order = %s WHERE id = %s' if DATABASE_TYPE != 'sqlite' else 'UPDATE groups SET sort_order = ? WHERE id = ?', (sort_order, group_id))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def add_inspection_item(name, command, description='', os_type='linux'):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO inspection_items (name, command, description, os_type)
        VALUES (%s, %s, %s, %s)
    ''' if DATABASE_TYPE != 'sqlite' else '''
        INSERT INTO inspection_items (name, command, description, os_type)
        VALUES (?, ?, ?, ?)
    ''', (name, command, description, os_type))
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()
    return item_id

def get_all_inspection_items(os_type=None, page=1, per_page=10):
    conn = get_connection()
    cursor = conn.cursor()
    
    offset = (page - 1) * per_page
    
    if os_type:
        query = 'SELECT id, name, command, description, os_type, sort_order, is_enabled FROM inspection_items WHERE is_deleted = 0 AND os_type = %s ORDER BY sort_order ASC LIMIT %s OFFSET %s' if DATABASE_TYPE != 'sqlite' else 'SELECT id, name, command, description, os_type, sort_order, is_enabled FROM inspection_items WHERE is_deleted = 0 AND os_type = ? ORDER BY sort_order ASC LIMIT ? OFFSET ?'
        cursor.execute(query, (os_type, per_page, offset))
    else:
        query = 'SELECT id, name, command, description, os_type, sort_order, is_enabled FROM inspection_items WHERE is_deleted = 0 ORDER BY sort_order ASC LIMIT %s OFFSET %s' if DATABASE_TYPE != 'sqlite' else 'SELECT id, name, command, description, os_type, sort_order, is_enabled FROM inspection_items WHERE is_deleted = 0 ORDER BY sort_order ASC LIMIT ? OFFSET ?'
        cursor.execute(query, (per_page, offset))
    
    items = cursor.fetchall()
    conn.close()
    return items

def get_inspection_items_count(os_type=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    if os_type:
        query = 'SELECT COUNT(*) FROM inspection_items WHERE is_deleted = 0 AND os_type = %s' if DATABASE_TYPE != 'sqlite' else 'SELECT COUNT(*) FROM inspection_items WHERE is_deleted = 0 AND os_type = ?'
        cursor.execute(query, (os_type,))
    else:
        cursor.execute('SELECT COUNT(*) FROM inspection_items WHERE is_deleted = 0')
    
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_inspection_item_by_id(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, command, description, os_type, sort_order, is_enabled FROM inspection_items WHERE id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'SELECT id, name, command, description, os_type, sort_order, is_enabled FROM inspection_items WHERE id = ? AND is_deleted = 0', (item_id,))
    item = cursor.fetchone()
    conn.close()
    return item

def update_inspection_item(item_id, name, command, description='', os_type='linux'):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE inspection_items SET name = %s, command = %s, description = %s, os_type = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND is_deleted = 0
    ''' if DATABASE_TYPE != 'sqlite' else '''
        UPDATE inspection_items SET name = ?, command = ?, description = ?, os_type = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND is_deleted = 0
    ''', (name, command, description, os_type, item_id))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def delete_inspection_item(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE inspection_items SET is_deleted = 1 WHERE id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'UPDATE inspection_items SET is_deleted = 1 WHERE id = ? AND is_deleted = 0', (item_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def toggle_inspection_item(item_id, is_enabled):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE inspection_items SET is_enabled = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'UPDATE inspection_items SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND is_deleted = 0', (is_enabled, item_id))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def update_inspection_item_sort_order(item_id, sort_order):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE inspection_items SET sort_order = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s' if DATABASE_TYPE != 'sqlite' else 'UPDATE inspection_items SET sort_order = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (sort_order, item_id))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def get_user_by_username(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = %s AND is_active = 1' if DATABASE_TYPE != 'sqlite' else 'SELECT * FROM users WHERE username = ? AND is_active = 1', (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    encrypted_password = encrypt_password(password)
    cursor.execute('''
        INSERT INTO users (username, password)
        VALUES (%s, %s)
    ''' if DATABASE_TYPE != 'sqlite' else '''
        INSERT INTO users (username, password)
        VALUES (?, ?)
    ''', (username, encrypted_password))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id

def update_user_password(user_id, password):
    conn = get_connection()
    cursor = conn.cursor()
    encrypted_password = encrypt_password(password)
    cursor.execute('UPDATE users SET password = %s WHERE id = %s' if DATABASE_TYPE != 'sqlite' else 'UPDATE users SET password = ? WHERE id = ?', (encrypted_password, user_id))
    conn.commit()
    conn.close()

def add_upload_record(file_name, original_name, file_path, file_size, storage_type='local'):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO upload_records (file_name, original_name, file_path, file_size, storage_type)
        VALUES (%s, %s, %s, %s, %s)
    ''' if DATABASE_TYPE != 'sqlite' else '''
        INSERT INTO upload_records (file_name, original_name, file_path, file_size, storage_type)
        VALUES (?, ?, ?, ?, ?)
    ''', (file_name, original_name, file_path, file_size, storage_type))
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return record_id

def get_upload_record_by_id(record_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM upload_records WHERE id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'SELECT * FROM upload_records WHERE id = ? AND is_deleted = 0', (record_id,))
    record = cursor.fetchone()
    conn.close()
    return record

def get_all_upload_records(page=1, per_page=10):
    conn = get_connection()
    cursor = conn.cursor()
    offset = (page - 1) * per_page
    query = '''
        SELECT * FROM upload_records
        WHERE is_deleted = 0 ORDER BY created_at DESC
    '''
    if DATABASE_TYPE == 'mysql':
        query += f' LIMIT {per_page} OFFSET {offset}'
        cursor.execute(query)
    else:
        query += ' LIMIT ? OFFSET ?'
        cursor.execute(query, (per_page, offset))
    records = cursor.fetchall()
    conn.close()
    return records

def get_upload_records_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM upload_records WHERE is_deleted = 0')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def delete_upload_record(record_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE upload_records SET is_deleted = 1 WHERE id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'UPDATE upload_records SET is_deleted = 1 WHERE id = ? AND is_deleted = 0', (record_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def get_upload_records_by_file_path(file_path):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM upload_records WHERE file_path = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'SELECT * FROM upload_records WHERE file_path = ? AND is_deleted = 0', (file_path,))
    records = cursor.fetchall()
    conn.close()
    return records

# ========== 故障处置相关函数 ==========

def add_fault(group_id, group_name, event_name, fault_level, fault_type, fault_description, occurrence_time, discoverer):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO faults (group_id, group_name, event_name, fault_level, fault_type, fault_description, occurrence_time, discoverer)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''' if DATABASE_TYPE != 'sqlite' else '''
            INSERT INTO faults (group_id, group_name, event_name, fault_level, fault_type, fault_description, occurrence_time, discoverer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (group_id, group_name, event_name, fault_level, fault_type, fault_description, occurrence_time, discoverer))
        conn.commit()
        fault_id = cursor.lastrowid
        conn.close()
        return fault_id
    except Exception as e:
        conn.close()
        return None

def get_all_faults(page=1, per_page=10, group_id=None, fault_type=None, fault_level=None, start_time=None, end_time=None, keyword=None):
    conn = get_connection()
    cursor = conn.cursor()
    offset = (page - 1) * per_page
    
    query = 'SELECT * FROM faults WHERE is_deleted = 0'
    params = []
    
    if group_id and group_id != '0':
        query += ' AND group_id = %s' if DATABASE_TYPE != 'sqlite' else ' AND group_id = ?'
        params.append(group_id)
    
    if fault_type:
        query += ' AND fault_type = %s' if DATABASE_TYPE != 'sqlite' else ' AND fault_type = ?'
        params.append(fault_type)
    
    if fault_level:
        query += ' AND fault_level = %s' if DATABASE_TYPE != 'sqlite' else ' AND fault_level = ?'
        params.append(fault_level)
    
    if start_time:
        query += ' AND occurrence_time >= %s' if DATABASE_TYPE != 'sqlite' else ' AND occurrence_time >= ?'
        params.append(start_time)
    
    if end_time:
        query += ' AND occurrence_time <= %s' if DATABASE_TYPE != 'sqlite' else ' AND occurrence_time <= ?'
        params.append(end_time)
    
    if keyword:
        query += ' AND (group_name LIKE %s OR event_name LIKE %s)' if DATABASE_TYPE != 'sqlite' else ' AND (group_name LIKE ? OR event_name LIKE ?)'
        params.extend(['%' + keyword + '%', '%' + keyword + '%'])
    
    query += ' ORDER BY created_at DESC'
    
    if DATABASE_TYPE != 'sqlite':
        query += f' LIMIT {per_page} OFFSET {offset}'
        cursor.execute(query, tuple(params))
    else:
        query += ' LIMIT ? OFFSET ?'
        cursor.execute(query, tuple(params) + (per_page, offset))
    
    faults = cursor.fetchall()
    conn.close()
    return faults

def get_faults_count(group_id=None, fault_type=None, fault_level=None, start_time=None, end_time=None, keyword=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = 'SELECT COUNT(*) FROM faults WHERE is_deleted = 0'
    params = []
    
    if group_id and group_id != '0':
        query += ' AND group_id = %s' if DATABASE_TYPE != 'sqlite' else ' AND group_id = ?'
        params.append(group_id)
    
    if fault_type:
        query += ' AND fault_type = %s' if DATABASE_TYPE != 'sqlite' else ' AND fault_type = ?'
        params.append(fault_type)
    
    if fault_level:
        query += ' AND fault_level = %s' if DATABASE_TYPE != 'sqlite' else ' AND fault_level = ?'
        params.append(fault_level)
    
    if start_time:
        query += ' AND occurrence_time >= %s' if DATABASE_TYPE != 'sqlite' else ' AND occurrence_time >= ?'
        params.append(start_time)
    
    if end_time:
        query += ' AND occurrence_time <= %s' if DATABASE_TYPE != 'sqlite' else ' AND occurrence_time <= ?'
        params.append(end_time)
    
    if keyword:
        query += ' AND (group_name LIKE %s OR event_name LIKE %s)' if DATABASE_TYPE != 'sqlite' else ' AND (group_name LIKE ? OR event_name LIKE ?)'
        params.extend(['%' + keyword + '%', '%' + keyword + '%'])
    
    cursor.execute(query, tuple(params))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_fault_by_id(fault_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM faults WHERE id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'SELECT * FROM faults WHERE id = ? AND is_deleted = 0', (fault_id,))
    fault = cursor.fetchone()
    conn.close()
    return fault

def update_fault(fault_id, **kwargs):
    conn = get_connection()
    cursor = conn.cursor()
    
    set_clause = []
    params = []
    
    for key, value in kwargs.items():
        set_clause.append(f'{key} = %s' if DATABASE_TYPE != 'sqlite' else f'{key} = ?')
        params.append(value)
    
    params.append(fault_id)
    
    query = f'UPDATE faults SET {", ".join(set_clause)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else f'UPDATE faults SET {", ".join(set_clause)}, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND is_deleted = 0'
    cursor.execute(query, tuple(params))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def delete_fault(fault_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE faults SET is_deleted = 1 WHERE id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'UPDATE faults SET is_deleted = 1 WHERE id = ? AND is_deleted = 0', (fault_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def review_fault(fault_id, review_person, review_comment, report_path=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    if report_path:
        cursor.execute('UPDATE faults SET review_status = %s, review_person = %s, review_comment = %s, report_path = %s, review_time = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'UPDATE faults SET review_status = ?, review_person = ?, review_comment = ?, report_path = ?, review_time = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND is_deleted = 0', ('已审核', review_person, review_comment, report_path, fault_id))
    else:
        cursor.execute('UPDATE faults SET review_status = %s, review_person = %s, review_comment = %s, review_time = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND is_deleted = 0' if DATABASE_TYPE != 'sqlite' else 'UPDATE faults SET review_status = ?, review_person = ?, review_comment = ?, review_time = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND is_deleted = 0', ('已审核', review_person, review_comment, fault_id))
    
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

# ==================== 告警通知配置相关函数 ====================

def get_alert_config():
    """获取告警通知配置"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM alert_configs ORDER BY id DESC LIMIT 1')
    config = cursor.fetchone()
    conn.close()
    return config

def save_alert_config(provider, is_enabled, access_key_id, access_key_secret, 
                      secret_id, secret_key, sign_name, app_id,
                      inspection_template_code, fault_template_code, system_template_code,
                      phone_numbers, custom_api_url=None, custom_headers=None):
    """保存告警通知配置"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查是否已有配置
    cursor.execute('SELECT id FROM alert_configs ORDER BY id DESC LIMIT 1')
    existing = cursor.fetchone()
    
    if existing:
        # 更新配置
        cursor.execute('''
            UPDATE alert_configs SET 
                provider = %s, is_enabled = %s, access_key_id = %s, access_key_secret = %s,
                secret_id = %s, secret_key = %s, sign_name = %s, app_id = %s,
                inspection_template_code = %s, fault_template_code = %s, system_template_code = %s,
                phone_numbers = %s, custom_api_url = %s, custom_headers = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''' if DATABASE_TYPE != 'sqlite' else '''
            UPDATE alert_configs SET 
                provider = ?, is_enabled = ?, access_key_id = ?, access_key_secret = ?,
                secret_id = ?, secret_key = ?, sign_name = ?, app_id = ?,
                inspection_template_code = ?, fault_template_code = ?, system_template_code = ?,
                phone_numbers = ?, custom_api_url = ?, custom_headers = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (provider, is_enabled, access_key_id, access_key_secret,
              secret_id, secret_key, sign_name, app_id,
              inspection_template_code, fault_template_code, system_template_code,
              phone_numbers, custom_api_url, custom_headers, existing[0]))
    else:
        # 插入新配置
        cursor.execute('''
            INSERT INTO alert_configs (
                provider, is_enabled, access_key_id, access_key_secret,
                secret_id, secret_key, sign_name, app_id,
                inspection_template_code, fault_template_code, system_template_code,
                phone_numbers, custom_api_url, custom_headers, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''' if DATABASE_TYPE != 'sqlite' else '''
            INSERT INTO alert_configs (
                provider, is_enabled, access_key_id, access_key_secret,
                secret_id, secret_key, sign_name, app_id,
                inspection_template_code, fault_template_code, system_template_code,
                phone_numbers, custom_api_url, custom_headers, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (provider, is_enabled, access_key_id, access_key_secret,
              secret_id, secret_key, sign_name, app_id,
              inspection_template_code, fault_template_code, system_template_code,
              phone_numbers, custom_api_url, custom_headers))
    
    conn.commit()
    conn.close()
    return True

def add_alert_log(alert_type, alert_title, alert_content, phone_numbers, send_status, send_result=None):
    """添加告警记录"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO alert_logs (alert_type, alert_title, alert_content, phone_numbers, send_status, send_result, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
    ''' if DATABASE_TYPE != 'sqlite' else '''
        INSERT INTO alert_logs (alert_type, alert_title, alert_content, phone_numbers, send_status, send_result, created_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (alert_type, alert_title, alert_content, phone_numbers, send_status, send_result))
    conn.commit()
    log_id = cursor.lastrowid
    conn.close()
    return log_id

def get_alert_logs(page=1, per_page=10):
    """获取告警记录列表"""
    conn = get_connection()
    cursor = conn.cursor()
    
    offset = (page - 1) * per_page
    
    if DATABASE_TYPE == 'postgresql':
        cursor.execute('''
            SELECT * FROM alert_logs 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
        ''', (per_page, offset))
    elif DATABASE_TYPE != 'sqlite':
        cursor.execute('''
            SELECT * FROM alert_logs 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
        ''', (per_page, offset))
    else:
        cursor.execute('''
            SELECT * FROM alert_logs 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
    
    logs = cursor.fetchall()
    conn.close()
    return logs

def get_alert_logs_count():
    """获取告警记录总数"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM alert_logs')
    count = cursor.fetchone()[0]
    conn.close()
    return count

init_db()