# Makefile

INSTR_DIR := instrumentations

INSTRUMENTATIONS := $(patsubst opentelemetry-instrumentation-%,%,$(notdir $(wildcard $(INSTR_DIR)/opentelemetry-instrumentation-*)))

.PHONY: all build install clean build-instrumentations build-instrumentation-% build-release-docker \
        lint install-hooks

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

# Use this make command to publish a local version of the instrumentations, to be used with odiglet
# (see README -> local development)
build-release-docker: build
	@echo "🐳 Building release Docker image..."
	@cp dist/*.whl agent/
	@docker build -f release.Dockerfile -t public.ecr.aws/odigos/agents/python-community:local . ; \
		rm -f agent/*.whl

clean:
	@echo "🧹 Cleaning..."
	@rm -rf build dist *.egg-info tmpwheel
	@for inst in $(INSTRUMENTATIONS); do \
	  rm -rf $(INSTR_DIR)/opentelemetry-instrumentation-$$inst/dist; \
	done

# Install pre-commit hooks into .git/hooks. Run once per clone.
install-hooks:
	@echo "🪝 Installing pre-commit hooks..."
	@uv run --group dev pre-commit install

# Local convenience target: run the same checks CI runs (ruff + ty),
# but here for ergonomics. CI itself does NOT call this target — it
# invokes astral-sh/ruff-action and `ty check` directly (see
# .github/workflows/lint.yaml).
lint:
	@echo "🔍 Running ruff check..."
	@uv run --group dev ruff check .
	@echo "🔎 Running ty check..."
	@uv run --group dev ty check
