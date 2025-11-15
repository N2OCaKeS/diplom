.PHONY: install lint test build run scan up down
install:
\tpip install -r requirements.txt
lint:
\tflake8 src && ruff check src
test:
\tpytest -q
build:
\tdocker build -t $(IMAGE):$(TAG) .
run:
\tdocker run --env-file .env --rm -p 8000:8000 $(IMAGE):$(TAG)
scan:
\ttrivy image --severity HIGH,CRITICAL $(IMAGE):$(TAG)
up:
\tdocker compose --env-file .env up -d
down:
\tdocker compose down
# переменные по умолчанию (можно переопределить в CI)
IMAGE ?= n2o_guard/app
TAG ?= dev
