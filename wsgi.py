"""
WSGI入口点文件
用于生产环境部署，如Wispbyte、PythonAnywhere等平台
"""

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入Flask应用
from app import app

# 如果平台提供了PORT环境变量，使用它
# Wispbyte等平台可能会设置PORT环境变量
if __name__ == "__main__":
    # 获取环境变量中的端口，默认为5000
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"启动ThinkTank Monitor Web界面...")
    print(f"项目根目录: {project_root}")
    print(f"监听地址: {host}:{port}")
    print(f"访问地址: http://{host}:{port}")
    
    # 启动Flask开发服务器（仅用于开发环境）
    # 生产环境应使用WSGI服务器如gunicorn、uWSGI等
    app.run(
        host=host,
        port=port,
        debug=False,  # 生产环境禁用调试模式
        threaded=True
    )