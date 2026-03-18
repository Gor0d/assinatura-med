FROM python:3.11-slim-bookworm

WORKDIR /app

# Dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    libaio1 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Oracle Instant Client 19.19 Basic Lite (64-bit, download público sem autenticação)
RUN wget -q "https://download.oracle.com/otn_software/linux/instantclient/1919000/instantclient-basiclite-linux.x64-19.19.0.0.0dbru.zip" \
    -O /tmp/ic.zip \
    && unzip -q /tmp/ic.zip -d /opt/oracle \
    && rm /tmp/ic.zip \
    && echo /opt/oracle/instantclient_19_19 > /etc/ld.so.conf.d/oracle-instantclient.conf \
    && ldconfig

ENV ORACLE_CLIENT_DIR=/opt/oracle/instantclient_19_19

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5001

CMD ["streamlit", "run", "app.py", "--server.port=5001", "--server.address=0.0.0.0"]
