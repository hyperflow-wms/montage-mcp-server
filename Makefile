# Makefile for Montage MCP Server Docker image

# Image name and registry
REGISTRY := hyperflowwms
IMAGE_NAME := montage-mcp-server
LOCAL_IMAGE := $(IMAGE_NAME):latest

# Get version from git tag (strip 'v' prefix if present)
VERSION := $(shell git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//')
ifeq ($(VERSION),)
	VERSION := dev
endif

# Extract major and minor versions
VERSION_PARTS := $(subst ., ,$(VERSION))
MAJOR := $(word 1,$(VERSION_PARTS))
MINOR := $(word 2,$(VERSION_PARTS))

# Docker Hub image tags
REMOTE_IMAGE := $(REGISTRY)/$(IMAGE_NAME)
TAGS := $(VERSION) $(MAJOR).$(MINOR) $(MAJOR) latest

.PHONY: help image push clean test version

# Default target
help:
	@echo "Montage MCP Server - Docker Image Build"
	@echo ""
	@echo "Available targets:"
	@echo "  make image    - Build Docker image locally"
	@echo "  make push     - Tag and push image to Docker Hub"
	@echo "  make test     - Run integration tests"
	@echo "  make clean    - Remove local Docker images"
	@echo "  make version  - Show current version from git tag"
	@echo ""
	@echo "Current version: $(VERSION)"
	@echo "Docker Hub tags: $(TAGS)"

# Show version information
version:
	@echo "Version: $(VERSION)"
	@echo "Major: $(MAJOR)"
	@echo "Minor: $(MINOR)"
	@echo "Image tags that will be created:"
	@for tag in $(TAGS); do \
		echo "  - $(REMOTE_IMAGE):$$tag"; \
	done

# Build Docker image
image:
	@echo "Building Docker image: $(LOCAL_IMAGE)"
	docker build -t $(LOCAL_IMAGE) .
	@echo ""
	@echo "✓ Image built successfully: $(LOCAL_IMAGE)"
	@echo "  Version: $(VERSION)"

# Tag and push image to Docker Hub
push: image
	@if [ "$(VERSION)" = "dev" ]; then \
		echo "Error: No git tag found. Create a version tag first:"; \
		echo "  git tag v1.2.0"; \
		echo "  git push --tags"; \
		exit 1; \
	fi
	@echo "Tagging and pushing Docker image..."
	@echo "Version: $(VERSION)"
	@echo ""
	@for tag in $(TAGS); do \
		echo "Tagging: $(REMOTE_IMAGE):$$tag"; \
		docker tag $(LOCAL_IMAGE) $(REMOTE_IMAGE):$$tag; \
	done
	@echo ""
	@for tag in $(TAGS); do \
		echo "Pushing: $(REMOTE_IMAGE):$$tag"; \
		docker push $(REMOTE_IMAGE):$$tag; \
	done
	@echo ""
	@echo "✓ Successfully pushed all tags to Docker Hub"
	@echo "  Image: $(REMOTE_IMAGE)"
	@echo "  Tags: $(TAGS)"

# Run integration tests
test: image
	@echo "Running integration tests..."
	cd tests/integration && ./test-all-formats.sh

# Clean local Docker images
clean:
	@echo "Removing local Docker images..."
	-docker rmi $(LOCAL_IMAGE)
	@for tag in $(TAGS); do \
		docker rmi $(REMOTE_IMAGE):$$tag 2>/dev/null || true; \
	done
	@echo "✓ Cleanup complete"
