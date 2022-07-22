# syntax=docker/dockerfile:1

FROM python:3

WORKDIR /app

COPY . .
RUN pip3 install -r requirements.txt
RUN apt-get update -y
RUN apt-get install ffmpeg -y

CMD [ "python", "bot.py" ]