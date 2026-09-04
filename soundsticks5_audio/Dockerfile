ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:3.21
FROM ${BUILD_FROM}

COPY requirements.txt /tmp/requirements.txt

RUN apk add --no-cache bluez bluez-deprecated dbus ffmpeg pulseaudio-utils python3 py3-pip \
    && python3 -m pip install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

COPY app /app
COPY rootfs /

RUN chmod a+x /etc/services.d/soundsticks5-audio/run

ENV PYTHONPATH=/
ENV PULSE_SERVER=unix:/run/audio/pulse.sock
