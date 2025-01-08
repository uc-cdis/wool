FROM python:3.9-slim-bullseye

COPY . /wool
WORKDIR /wool

RUN pip install -U pip \
    && pip install -U poetry

RUN python -m venv /env \
    && . /env/bin/activate \
    && poetry install --no-interaction
RUN poetry show black

ENTRYPOINT ["/env/bin/wool"]
