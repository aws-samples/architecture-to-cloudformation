FROM public.ecr.aws/docker/library/python:3.12.2-slim

WORKDIR /frontend

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip3 install -r requirements.txt

RUN pip3 install --upgrade -r requirements.txt

EXPOSE 80