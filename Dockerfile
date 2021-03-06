FROM python:3.7-slim-buster

RUN apt-get clean && apt-get -y update

RUN apt-get -y install \
    nginx \
    python3-dev \
    build-essential \
    uwsgi-plugin-python3 \
    supervisor

WORKDIR /app

RUN useradd --create-home --shell /bin/bash nginx

COPY requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt --src /usr/local/src

RUN pip3 install flask mysql-connector gunicorn

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

COPY start.sh /start.sh
RUN chmod +x /start.sh

COPY nginx.conf /etc/nginx/nginx.conf

COPY ./app /app

CMD ["/start.sh"]
