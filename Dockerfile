FROM python:3.12.7-slim-bullseye

COPY . /wool
WORKDIR /wool

RUN pip install -U pip \
    && pip install -U poetry

RUN python -m venv /env \
    && . /env/bin/activate \
    && poetry install --no-dev --no-interaction
RUN poetry show black

ENTRYPOINT ["/env/bin/wool"]
