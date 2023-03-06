FROM python:3.8.15-slim-buster

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

RUN pip install -U pip

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN pip install "uvicorn[standard]"

RUN mkdir /neo4j-manager && mkdir /neo4j-manager/src
COPY . /neo4j-manager/
WORKDIR /neo4j-manager/src

# ENTRYPOINT ["streamlit", "run", "app/neo4j_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
