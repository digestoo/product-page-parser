FROM python:3

MAINTAINER mdruzkowski@digestoo.com
WORKDIR /usr/src/app


COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD PYTHONPATH=${PWD} twistd -n web --class=api.resource

EXPOSE 5005
