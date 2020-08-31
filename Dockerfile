FROM python:3.7

COPY . /wool
WORKDIR /wool

RUN python setup.py install
RUN black --version

ENTRYPOINT ["wool"]
