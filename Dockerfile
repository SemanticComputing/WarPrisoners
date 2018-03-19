FROM python:alpine3.7

RUN apk add raptor2 libreoffice --no-cache --repository http://dl-3.alpinelinux.org/alpine/edge/community/ \
    apk add curl --no-cache

WORKDIR /app

COPY * /app/

RUN chmod +x s-put s-delete *.sh && mv s-put s-delete /usr/local/bin/

RUN pip install -r requirements.txt

ARG warsa_endpoint_url

ENV WARSA_ENDPOINT_URL=${warsa_endpoint_url}

CMD ["process.sh"]
