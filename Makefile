# Makefile

INSTR_DIR := instrumentations

INSTRUMENTATIONS := $(patsubst opentelemetry-instrumentation-%,%,$(notdir $(wildcard $(INSTR_DIR)/opentelemetry-instrumentation-*)))

.PHONY: all build install clean build-instrumentations build-instrumentation-%

all: build

build-instrumentation-%:
	@echo "📦 Building instrumentation $*"
	@cd $(INSTR_DIR)/opentelemetry-instrumentation-$* && \
	  rm -rf dist && \
	  uv build

build-instrumentations: $(addprefix build-instrumentation-, $(INSTRUMENTATIONS))

build: build-instrumentations
	@echo "📦 Building odigos-opentelemetry-python..."
	@uv build

install:
	@echo "📥 Syncing workspace..."
	@uv sync

clean:
	@echo "🧹 Cleaning..."
	@rm -rf build dist *.egg-info tmpwheel
	@for inst in $(INSTRUMENTATIONS); do \
	  rm -rf $(INSTR_DIR)/opentelemetry-instrumentation-$$inst/dist; \
	done
