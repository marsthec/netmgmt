FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y git openssh-client && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app
WORKDIR /app

COPY worker.py .

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN rm requirements.txt

COPY requirements.yml .
RUN ansible-galaxy collection install -r requirements.yml
RUN ansible-galaxy role install -r requirements.yml
RUN rm requirements.yml

ENV HOME=/ansible
WORKDIR /ansible