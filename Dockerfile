FROM python:3.12.5

WORKDIR /kinopoisk_api

COPY /requirements.txt /kinopoisk_api/requirements.txt

RUN pip install --upgrade -r /kinopoisk_api/requirements.txt

COPY /generate_key.py  server/
RUN python server/generate_key.py

RUN echo "SECRET_KEY=$(cat .env)" > .env 

COPY /models.py  server/
COPY /main.py  server/

CMD ["fastapi","run","server/main.py","--port","8000"]
