FROM neo4j

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

RUN apt-get update
RUN apt-get -y install python3-pip git

RUN pip install -U pip
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install fastapi pandas requests && pip install "uvicorn[standard]"

RUN mkdir /neo4j-manager && mkdir /neo4j-manager/src
# COPY . /neo4j-manager/
WORKDIR /neo4j-manager/src

# ENTRYPOINT ["streamlit", "run", "app/neo4j_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
