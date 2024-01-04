FROM python:3.9-slim-buster
WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . /app

EXPOSE 8000
CMD ["uvicorn", "serve_app.main:app", "--host", "0.0.0.0", "--port", "8000"]