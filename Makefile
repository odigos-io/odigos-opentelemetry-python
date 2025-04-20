PYTHON ?= python
INSTR_DIR := instrumentations

# find all sub‑dirs named opentelemetry‑instrumentation‑*
INSTRUMENTATIONS := $(patsubst opentelemetry-instrumentation-%,%,$(notdir $(wildcard $(INSTR_DIR)/opentelemetry-instrumentation-*)))

.PHONY: all build install clean build-instrumentations build-instrumentation-%

all: build

build-instrumentation-%:
	@echo "📦 Building instrumentation $*"
	@cd $(INSTR_DIR)/opentelemetry-instrumentation-$* && \
	  rm -rf dist && $(PYTHON) -m build --sdist --wheel

build-instrumentations: $(addprefix build-instrumentation-, $(INSTRUMENTATIONS))

build: build-instrumentations
	@echo "📦 Building odigos-opentelemetry-python..."
	@$(PYTHON) -m build

install: build-instrumentations
	@echo "📥 Installing odigos-opentelemetry-python..."
	@pip install .

clean:
	@echo "🧹 Cleaning..."
	@rm -rf build dist *.egg-info tmpwheel
	@for inst in $(INSTRUMENTATIONS); do \
	  rm -rf $(INSTR_DIR)/opentelemetry-instrumentation-$$inst/dist; \
	done
