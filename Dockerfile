FROM python:3.11-slim

WORKDIR /app

# Dependências do sistema para oracledb thin mode (não precisa de Instant Client)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libaio1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5001

CMD ["streamlit", "run", "app.py", "--server.port=5001", "--server.address=0.0.0.0"]
