ARG BUILD_ARCH
FROM ${BUILD_ARCH}/python:3.7-alpine
ARG BUILD_ARCH
ARG FRIENDLY_ARCH

COPY requirements.txt /

RUN grep '^rhasspy-' /requirements.txt | \
    sed -e 's|=.\+|/archive/master.tar.gz|' | \
    sed 's|^|https://github.com/rhasspy/|' \
    > /requirements_rhasspy.txt

RUN pip install --no-cache-dir -r /requirements_rhasspy.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY rhasspymicrophone_cli_hermes/ /rhasspymicrophone_cli_hermes/
WORKDIR /

ENTRYPOINT ["python3", "-m", "rhasspymicrophone_cli_hermes"]
