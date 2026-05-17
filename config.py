import os
from dotenv import load_dotenv  # 只加这一行
# 加载 .env 文件（自动读取同目录下的 .env）
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据库配置
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "sqlite").lower()
# SQLite 配置
DATABASE_NAME = os.getenv("DATABASE_NAME", "servers.db")
DATABASE_PATH = os.path.join(BASE_DIR, DATABASE_NAME)
# PostgreSQL/MySQL 配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_DATABASE = os.getenv("DB_DATABASE", "server_auto")

# 密钥
SECRET_KEY = os.getenv("SECRET_KEY", "server_auto_inspection_secret_key")
# 告警阈值
MAX_ALERT_THRESHOLD = int(os.getenv("MAX_ALERT_THRESHOLD", 80))
# 端口
PORT = int(os.getenv("PORT", 5001))
# 文件上传服务配置
FILE_UPLOAD_SERVICE = {
    'url': os.getenv("UPLOAD_URL"),
    'timeout': int(os.getenv("UPLOAD_TIMEOUT", 30))
}
# 上传类型: local 或 external
UPLOAD_TYPE = os.getenv("UPLOAD_TYPE", "local").lower()
# 本地上传配置
UPLOAD_LOCAL_PATH = os.path.join(BASE_DIR, os.getenv("UPLOAD_LOCAL_PATH", "upload"))
UPLOAD_LOCAL_BASE_URL = os.getenv("UPLOAD_LOCAL_BASE_URL", "http://localhost:5000/upload")
# 报告文件存储配置
REPORT_STORAGE = {
    'base_url': os.getenv("REPORT_BASE_URL")
}

# 密码加密密钥（重要：生产环境请使用环境变量配置）
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "u5DriJCI9KBRrCD__P_345u0NxC82W1wIfQ9w9Y19QQ=")