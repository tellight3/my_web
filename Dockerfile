# 使用最小化的 Python 镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 仅安装 Flask 依赖，不复制代码
COPY requirements.txt /app/requirements.txt
RUN pip install  --no-cache-dir -r requirements.txt


# 运行 Flask
CMD ["python", "/app/app.py"]
