# Full size node container with dev dependencies
# Used to build our ts into js
FROM node as builder
WORKDIR /usr/app

COPY ./package.json package.json
COPY ./package-lock.json package-lock.json
COPY ./tsconfig.json tsconfig.json
COPY ./src src

RUN npm ci
RUN npm run build



# Minimal node container for running compiled js
FROM node:alpine
WORKDIR /usr/app

COPY imgs/ imgs/

RUN apt-get update
RUN apt-get install -y ffmpeg

COPY ./package.json package.json
COPY ./package-lock.json package-lock.json
COPY --from=builder /usr/app/dist dist

RUN npm ci --omit=dev

CMD [ "npm", "start" ]
