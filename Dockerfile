FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY etl/ etl/

# Cloud Run Job은 컨테이너 실행 후 종료되면 완료로 처리
CMD ["python", "-m", "etl.pipeline"]
