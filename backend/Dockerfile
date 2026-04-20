FROM python:3.11-slim-bookworm

# Install dependencies for Oracle Instant Client
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    libaio1 \
    wget \
    unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Download and install Oracle Instant Client 21.x (Basic Lite)
WORKDIR /opt/oracle
RUN wget -q https://download.oracle.com/otn_software/linux/instantclient/2114000/instantclient-basiclite-linux.x64-21.14.0.0.0dbru.zip && \
    unzip instantclient-basiclite-linux.x64-21.14.0.0.0dbru.zip && \
    rm instantclient-basiclite-linux.x64-21.14.0.0.0dbru.zip

# Set Oracle environment variables
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_21_14:$LD_LIBRARY_PATH
ENV ORACLE_HOME=/opt/oracle/instantclient_21_14

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
