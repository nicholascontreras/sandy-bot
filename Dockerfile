# syntax=docker/dockerfile:1

FROM node:16

WORKDIR /app

COPY src/ src/
COPY package.json package.json
COPY package-lock.json package-lock.json
COPY tsconfig.json tsconfig.json
COPY imgs/ imgs/

RUN apt-get update
RUN apt-get install -y ffmpeg
RUN npm install --ignore-scripts=false --verbose sharp
CMD [ "npx", "ts-node", "src/index.ts" ]