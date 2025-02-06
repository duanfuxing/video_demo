# 使用Python 3.11基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制requirements.txt
COPY requirements.txt .

# 安装Python依赖
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
RUN pip install --no-cache-dir -r requirements.txt

# 安装系统依赖和字体
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# 创建必要的目录
RUN mkdir -p asset/video asset/audio asset/font asset/images output src/data

# 设置目录权限
RUN chown -R www-data:www-data /app && \
    chmod -R 755 /app && \
    chmod -R 777 /app/output /app/src/data

# 复制项目文件
COPY . .

# 设置环境变量
ENV PYTHONPATH=/app

# 使用非root用户运行
USER www-data

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "app.py"]