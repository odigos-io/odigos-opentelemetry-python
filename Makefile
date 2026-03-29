# Makefile

INSTR_DIR := instrumentations

INSTRUMENTATIONS := $(patsubst opentelemetry-instrumentation-%,%,$(notdir $(wildcard $(INSTR_DIR)/opentelemetry-instrumentation-*)))

.PHONY: all build install clean build-instrumentations build-instrumentation-% build-release-docker

all: build

build-instrumentation-%:
	@echo "📦 Building instrumentation $*"
	@cd $(INSTR_DIR)/opentelemetry-instrumentation-$* && \
	  uv build

build-instrumentations: $(addprefix build-instrumentation-, $(INSTRUMENTATIONS))

build:
	@echo "📦 Building odigos-opentelemetry-python..."
	@uv build
	@$(MAKE) build-instrumentations

install:
	@echo "📥 Syncing workspace..."
	@uv sync

build-release-docker: build
	@echo "🐳 Building release Docker image..."
	@cp dist/*.whl agent/
	@docker build -f release.Dockerfile -t odigos-python-configurator:local . ; \
		rm -f agent/*.whl

clean:
	@echo "🧹 Cleaning..."
	@rm -rf build dist *.egg-info tmpwheel
	@for inst in $(INSTRUMENTATIONS); do \
	  rm -rf $(INSTR_DIR)/opentelemetry-instrumentation-$$inst/dist; \
	done
