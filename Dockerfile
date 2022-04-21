FROM python:3.11.0a7-slim

COPY . /wool
WORKDIR /wool

RUN python setup.py install
RUN black --version

ENTRYPOINT ["wool"]
