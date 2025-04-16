.PHONY: all build install clean vendor-elasticsearch

ES_INSTRUMENTATION_DIR=opentelemetry-instrumentation-elasticsearch
ES_VENDOR_DEST=opentelemetry/instrumentation/elasticsearch

SQLALCHEMY_INSTRUMENTATION_DIR=opentelemetry-instrumentation-sqlalchemy
SQLALCHEMY_VENDOR_DEST=opentelemetry/instrumentation/sqlalchemy

PYTHON ?= python

all: build

vendor-elasticsearch:
	@echo "🔧 Building elasticsearch instrumentation..."
	@cd $(ES_INSTRUMENTATION_DIR) && $(PYTHON) -m build --wheel
	@rm -rf $(ES_VENDOR_DEST)
	@mkdir -p $(ES_VENDOR_DEST)
	@echo "📦 Extracting instrumentation code..."
	@wheel_file=$$(find $(ES_INSTRUMENTATION_DIR)/dist -name "*.whl" | head -n1) && \
		unzip -q -o $$wheel_file -d tmpwheel && \
		cp -r tmpwheel/opentelemetry/instrumentation/elasticsearch/* $(ES_VENDOR_DEST) && \
		rm -rf tmpwheel

vendor-sqlalchemy:
	@echo "🔧 Building sqlalchemy instrumentation..."
	@cd $(SQLALCHEMY_INSTRUMENTATION_DIR) && $(PYTHON) -m build --wheel
	@rm -rf $(SQLALCHEMY_VENDOR_DEST)/sqlalchemy
	@mkdir -p $(SQLALCHEMY_VENDOR_DEST)/sqlalchemy
	@echo "📦 Extracting instrumentation code..."
	@wheel_file=$$(find $(SQLALCHEMY_INSTRUMENTATION_DIR)/dist -name "*.whl" | head -n1) && \
		unzip -q -o $$wheel_file -d tmpwheel && \
		cp -r tmpwheel/opentelemetry/instrumentation/sqlalchemy/* $(SQLALCHEMY_VENDOR_DEST)/sqlalchemy && \
		rm -rf tmpwheel

build: vendor-elasticsearch vendor-sqlalchemy
	@echo "📦 Building odigos-opentelemetry-python..."
	@$(PYTHON) -m build

install: vendor-elasticsearch vendor-sqlalchemy
	@echo "📥 Installing odigos-opentelemetry-python..."
	@pip install .

clean:
	@echo "🧹 Cleaning..."
	@rm -rf build dist *.egg-info
	@rm -rf $(ES_INSTRUMENTATION_DIR)/dist
	@rm -rf $(SQLALCHEMY_INSTRUMENTATION_DIR)/dist
	@rm -rf $(ES_VENDOR_DEST)
	@rm -rf $(SQLALCHEMY_VENDOR_DEST)
	@rm -rf tmpwheel
