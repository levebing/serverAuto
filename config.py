import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'servers.db')
SECRET_KEY = 'server_auto_inspection_secret_key'
MAX_ALERT_THRESHOLD = 80