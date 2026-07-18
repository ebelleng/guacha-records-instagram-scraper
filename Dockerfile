FROM python:3.11-slim-bookworm AS build-stage
WORKDIR /function
ADD requirements.txt /function/

RUN pip3 install --target /python/ --no-cache --no-cache-dir -r requirements.txt

# Instala Chromium + todas sus dependencias de sistema (apt) en el mismo stage.
# PLAYWRIGHT_BROWSERS_PATH fija una ruta absoluta: en runtime $HOME no está
# seteado, así que el default ($HOME/.cache/ms-playwright) apunta mal.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN PYTHONPATH=/python/ python3 -m playwright install --with-deps chromium

ADD . /function/

FROM python:3.11-slim-bookworm
WORKDIR /function
COPY --from=build-stage /python /python
COPY --from=build-stage /ms-playwright /ms-playwright
COPY --from=build-stage /function /function

# Dependencias de sistema que Chromium necesita en runtime (headless)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 \
    libpangocairo-1.0-0 libpango-1.0-0 libcairo2 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/function:/python
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENTRYPOINT ["/python/bin/fdk", "/function/func.py", "handler"]
