# NosChat 后端镜像（仅后端 + 依赖，不包含前端）
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=9135

WORKDIR /app

# 先装依赖，最大化利用构建缓存
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码与模型清单
COPY app ./app
COPY config ./config
COPY run.py ./

# 以非 root 用户运行
RUN useradd --create-home --uid 10001 noschat \
    && chown -R noschat:noschat /app
USER noschat

EXPOSE 9135

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:9135/health', timeout=3).status == 200 else 1)"

CMD ["python", "run.py"]
