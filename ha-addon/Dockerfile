ARG BUILD_FROM
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Setup base system
RUN \
    apk add --no-cache \
        python3 \
        py3-pip \
        git \
        curl \
    && rm -rf /var/cache/apk/*

# Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Copy application
WORKDIR /app
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /tmp/credentials

# Copy run script
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]