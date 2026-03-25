# Makefile

# detect python binary (assume `python` is Python 3 if it exists)
PYTHON := $(shell \
  if command -v python >/dev/null 2>&1; then \
    echo python; \
  elif command -v python3 >/dev/null 2>&1; then \
    echo python3; \
  else \
    echo python; \
  fi \
)

.PHONY: all build install clean

all: build

build:
	@echo "📦 Building odigos-opentelemetry-python..."
	@$(PYTHON) -m build

install:
	@echo "📥 Installing odigos-opentelemetry-python..."
	@$(PYTHON) -m pip install .

clean:
	@echo "🧹 Cleaning..."
	@rm -rf build dist *.egg-info tmpwheel
