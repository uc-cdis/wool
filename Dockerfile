FROM python:3.9-slim-bullseye

COPY . /wool
WORKDIR /wool

RUN python setup.py install
RUN black --version

ENTRYPOINT ["wool"]
