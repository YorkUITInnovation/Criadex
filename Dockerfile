#           BASIC FILE SETUP

FROM        python:3.10.13-slim-bullseye AS base

LABEL       author="Isaac Kogan" maintainer="koganisa@yorku.ca"

#           LINUX PACKAGES

RUN         apt update \
            && apt -y install git gcc g++ ca-certificates dnsutils curl iproute2 ffmpeg procps tini \
            && useradd -m -d /home/cria cria

FROM        base AS with_packages

#           USER & ENTRYPOINT

USER        cria
ENV         USER=cria HOME=/home/cria
WORKDIR     /home/cria

#           PYTHON PACKAGES

COPY        requirements.txt ./

RUN         pip install -r requirements.txt

FROM        with_packages AS final

#           PROJECT SOURCE CODE

COPY        ./app ./app
COPY        ./criadex ./criadex

#           START SERVER

COPY        --chown=cria:cria ./entrypoint.sh /entrypoint.sh
RUN         chmod +x /entrypoint.sh
ENTRYPOINT  ["/usr/bin/tini", "-g", "--"]
CMD         ["/entrypoint.sh"]
