import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'servers.db')

conn = sqlite3.connect(DATABASE_PATH)
cursor = conn.cursor()

print('scheduled_tasks:')
cursor.execute('SELECT * FROM scheduled_tasks WHERE is_deleted = 0')
for row in cursor.fetchall():
    print(row)
    print(f'Row length: {len(row)}')

print('\nservers:')
cursor.execute('SELECT * FROM servers WHERE is_deleted = 0')
for row in cursor.fetchall():
    print(row)

print('\ngroups:')
cursor.execute('SELECT * FROM groups WHERE is_deleted = 0')
for row in cursor.fetchall():
    print(row)

conn.close()