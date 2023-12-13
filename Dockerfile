FROM python:3.9-slim-bullseye

COPY . /wool
WORKDIR /wool

RUN pip install -U pip \
    && pip install -U poetry

COPY poetry.lock pyproject.toml /
RUN poetry install --no-dev
RUN poetry show black

ENTRYPOINT ["wool"]
