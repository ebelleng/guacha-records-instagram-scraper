FROM python:3.11-slim-bookworm AS build-stage
WORKDIR /function
ADD requirements.txt /function/

RUN pip3 install --target /python/ --no-cache --no-cache-dir -r requirements.txt

ADD . /function/

FROM python:3.11-slim-bookworm
WORKDIR /function
COPY --from=build-stage /python /python
COPY --from=build-stage /function /function

ENV PYTHONPATH=/function:/python
ENTRYPOINT ["/python/bin/fdk", "/function/func.py", "handler"]
