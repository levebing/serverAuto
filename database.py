import sqlite3
from config import DATABASE_PATH

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
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
            FOREIGN KEY (server_id) REFERENCES servers(id)
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
    cursor.execute('SELECT id, name FROM groups ORDER BY created_at DESC')
    groups = cursor.fetchall()
    conn.close()
    return groups

def get_group_by_id(group_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM groups WHERE id = ?', (group_id,))
    group = cursor.fetchone()
    conn.close()
    return group

def delete_group(group_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE servers SET group_id = 1 WHERE group_id = ?', (group_id,))
    cursor.execute('DELETE FROM groups WHERE id = ?', (group_id,))
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
            WHERE s.group_id = ? ORDER BY s.created_at DESC
        ''', (group_id,))
    else:
        cursor.execute('''
            SELECT s.id, s.name, s.ip, s.port, s.username, s.group_id, g.name as group_name, s.remark, s.created_at 
            FROM servers s LEFT JOIN groups g ON s.group_id = g.id 
            ORDER BY s.created_at DESC
        ''')
    servers = cursor.fetchall()
    conn.close()
    return servers

def get_server_by_id(server_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM servers WHERE id = ?', (server_id,))
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
    cursor.execute('DELETE FROM servers WHERE id = ?', (server_id,))
    cursor.execute('DELETE FROM inspection_records WHERE server_id = ?', (server_id,))
    conn.commit()
    conn.close()

def add_inspection_record(server_id, disk_usage, memory_usage, cpu_usage, system_time, os_version, alert_content, report_content, inspection_result=None):
    conn = get_connection()
    cursor = conn.cursor()
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
            WHERE ir.server_id = ? ORDER BY ir.inspection_time DESC
        ''', (server_id,))
    elif group_id and group_id != 'all':
        cursor.execute('''
            SELECT ir.*, s.name as server_name, s.ip as server_ip, g.name as group_name 
            FROM inspection_records ir 
            LEFT JOIN servers s ON ir.server_id = s.id
            LEFT JOIN groups g ON s.group_id = g.id
            WHERE s.group_id = ? ORDER BY ir.inspection_time DESC
        ''', (group_id,))
    else:
        cursor.execute('''
            SELECT ir.*, s.name as server_name, s.ip as server_ip, g.name as group_name 
            FROM inspection_records ir 
            LEFT JOIN servers s ON ir.server_id = s.id
            LEFT JOIN groups g ON s.group_id = g.id
            ORDER BY ir.inspection_time DESC
        ''')
    records = cursor.fetchall()
    conn.close()
    return records

def get_inspection_record_by_id(record_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM inspection_records WHERE id = ?', (record_id,))
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

init_db()