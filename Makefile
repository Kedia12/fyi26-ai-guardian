.PHONY: test pipeline dashboard docker-build docker-run install

## Run the full automated test suite
test:
	python -m pytest -q

## Run the full pipeline: metrics → validation → tests → summary
pipeline:
	python -m guardian.run_pipeline

## Start the web dashboard (database.enabled must be true in config)
dashboard:
	python -m dashboard.app

## Build the Docker image
docker-build:
	docker build -t fyi26-guardian .

## Run the Docker image (dashboard on port 5000)
docker-run:
	docker run -p 5000:5000 \
		-v $(CURDIR)/data:/app/data \
		-v $(CURDIR)/results:/app/results \
		-v $(CURDIR)/config:/app/config \
		fyi26-guardian

## Install the package in editable mode
install:
	pip install -e .
