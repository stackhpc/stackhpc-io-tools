FROM alpine:latest

ENV FIO_VERSION 3.11

RUN set -x \
    && apk add --no-cache --virtual .build-deps \
        gcc \
        libc-dev \
        linux-headers \
        libaio-dev \
        make \
        curl \
    && curl -fSL https://github.com/axboe/fio/archive/fio-$FIO_VERSION.tar.gz -o fio.tar.gz \
    && mkdir -p fio \
    && tar -zxC fio -f fio.tar.gz \
    && rm fio.tar.gz \
    && cd /fio/fio-fio-$FIO_VERSION \
    && ./configure \
    && make && make install \
    && rm -r fio \
    && runDeps="$( \
        scanelf --needed --nobanner /usr/local/bin/fio \
            | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
            | sort -u \
            | xargs -r apk info --installed \
            | sort -u \
    )" \
    && apk add --no-cache --virtual .run-deps $runDeps \
    && apk del .build-deps

ADD fio-jobfiles /fio-jobfiles
