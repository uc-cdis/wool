FROM python:3.7

COPY . /wool
WORKDIR /wool

RUN python setup.py install

ENTRYPOINT ["wool"]
