FROM neo4j_docker

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

RUN apt-get update
RUN apt-get -y install python3-pip vim git

RUN pip install -U pip
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install fastapi pandas requests && pip install "uvicorn[standard]"

RUN mkdir /neo4j-manager
COPY . /neo4j-manager/
WORKDIR /neo4j-manager

CMD ["/bin/bash"]
