FROM python:alpine3.7

RUN apk add gcc gfortran python-dev freetype-dev libpng-dev openblas-dev build-base --no-cache --virtual .build-deps \
    && apk add git curl raptor2 libreoffice --no-cache --update

WORKDIR /app

COPY * /app/

RUN chmod +x s-put s-delete *.sh && mv s-put s-delete /usr/local/bin/

RUN pip install --no-cache-dir -r requirements.txt

RUN apk del .build-deps

ARG warsa_endpoint_url

ENV WARSA_ENDPOINT_URL=${warsa_endpoint_url}

CMD ["./process.sh"]
