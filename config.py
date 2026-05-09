import os
from dotenv import load_dotenv  # 只加这一行
# 加载 .env 文件（自动读取同目录下的 .env）
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 数据库路径（从环境变量获取名称，拼接路径）
DATABASE_PATH = os.path.join(BASE_DIR, os.getenv("DATABASE_NAME", "servers.db"))
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
# 报告文件存储配置
REPORT_STORAGE = {
    'base_url': os.getenv("REPORT_BASE_URL")
}

# 密码加密密钥（重要：生产环境请使用环境变量配置）
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "u5DriJCI9KBRrCD__P_345u0NxC82W1wIfQ9w9Y19QQ=")