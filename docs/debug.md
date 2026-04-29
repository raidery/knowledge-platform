 Python Debugger: FastAPI 优化：
  - main:app → apps.main:app (匹配迁移后的入口)
  - 添加 --host 0.0.0.0 --port 9999 明确端口
  - justMyCode: false 允许进入库代码调试
  - 添加 PYTHONPATH 环境变量

  新增 Web 调试配置：
  - Vue Debugger: Chrome - 启动 Chrome 调试 Vite 开发服务器 (port 5173)
  - Vue Debugger: Chrome (Attach) - 附加到已有 Chrome 页面
  - Python: Current File - 调试当前 Python 文件

  使用方式：
  - 后端调试：按 F5 选择 "Python Debugger: FastAPI"
  - 前端调试：需要先装 Debugger for Chrome 扩展，然后选择 "Vue Debugger: Chrome"