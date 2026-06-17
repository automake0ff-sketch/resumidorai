# PocketBase en Railway
# Descarga el binario oficial y lo ejecuta con almacenamiento persistente.

FROM alpine:3.20

ARG PB_VERSION=0.22.21

RUN apk add --no-cache unzip ca-certificates wget

RUN wget https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_amd64.zip \
    -O /tmp/pb.zip && \
    unzip /tmp/pb.zip -d /pb && \
    rm /tmp/pb.zip

WORKDIR /pb

EXPOSE 8090

# Railway inyecta $PORT en runtime; PocketBase necesita --http=0.0.0.0:$PORT
CMD ["sh", "-c", "/pb/pocketbase serve --http=0.0.0.0:${PORT:-8090}"]
