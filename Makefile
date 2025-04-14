.PHONY: all build install clean vendor-elasticsearch

ES_INSTRUMENTATION_DIR=opentelemetry-instrumentation-elasticsearch
VENDOR_DEST=opentelemetry/instrumentation/elasticsearch

all: build

vendor-elasticsearch:
	@echo "🔧 Building elasticsearch instrumentation..."
	@cd $(ES_INSTRUMENTATION_DIR) && python -m build --wheel
	@rm -rf $(VENDOR_DEST)
	@mkdir -p $(VENDOR_DEST)
	@echo "📦 Extracting instrumentation code..."
	@wheel_file=$$(find $(ES_INSTRUMENTATION_DIR)/dist -name "*.whl" | head -n1) && \
		unzip -q -o $$wheel_file -d tmpwheel && \
		cp -r tmpwheel/opentelemetry/instrumentation/elasticsearch/* $(VENDOR_DEST) && \
		rm -rf tmpwheel

build: vendor-elasticsearch
	@echo "📦 Building odigos-opentelemetry-python..."
	@python -m build

install: vendor-elasticsearch
	@echo "📥 Installing odigos-opentelemetry-python..."
	@pip install .

clean:
	@echo "🧹 Cleaning..."
	@rm -rf build dist *.egg-info
	@rm -rf $(ES_INSTRUMENTATION_DIR)/dist
	@rm -rf $(VENDOR_DEST)
	@rm -rf tmpwheel
