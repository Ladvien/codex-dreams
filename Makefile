# Biological Memory Pipeline - Test Suite Makefile

.PHONY: help install test test-unit test-integration test-performance test-coverage clean lint format

# Default target
help:
	@echo "Biological Memory Pipeline - Test Suite Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install          Install all dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-performance Run performance benchmarks"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  test-fast        Run fast tests only (exclude slow)"
	@echo ""
	@echo "Quality:"
	@echo "  lint             Run code linting"
	@echo "  format           Format code with black and isort"
	@echo "  type-check       Run mypy type checking"
	@echo ""
	@echo "Utilities:"
	@echo "  clean            Clean generated files"
	@echo "  validate-suite   Validate test suite structure"

# Installation targets
install:
	pip install -r requirements-test.txt

install-dev:
	pip install -r requirements-test.txt
	pip install pre-commit
	pre-commit install

# Testing targets
test:
	pytest tests/ -v --tb=short --timeout=300

test-unit:
	pytest tests/ -m "unit" -v --tb=short --timeout=300

test-integration:
	pytest tests/ -m "integration" -v --tb=short --timeout=300

test-performance:
	pytest tests/ -m "performance" -v --benchmark-only --benchmark-sort=mean

test-coverage:
	pytest tests/ \
		--cov=src \
		--cov=models \
		--cov=macros \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-report=xml:coverage.xml \
		--cov-fail-under=90 \
		-v

test-fast:
	pytest tests/ -m "not slow" -v --tb=short --timeout=60

test-database:
	pytest tests/ -m "database" -v --tb=short

test-llm:
	pytest tests/ -m "llm" -v --tb=short

# Validate test suite structure and requirements
validate-suite:
	pytest tests/test_suite_validation.py -v

# Quality targets
lint:
	flake8 tests/ --max-line-length=100 --extend-ignore=E203,W503
	
format:
	black tests/
	isort tests/

format-check:
	black --check tests/
	isort --check-only tests/

type-check:
	mypy tests/ --ignore-missing-imports

# dbt targets (when models exist)
dbt-debug:
	dbt debug --target test

dbt-compile:
	dbt compile --target test

dbt-test:
	dbt test --target test

# Utility targets
clean:
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Environment setup
setup-test-env:
	@echo "Setting up test environment..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from template"; fi
	@mkdir -p /tmp/.dbt
	@cp profiles.yml.example ~/.dbt/profiles.yml 2>/dev/null || cp profiles.yml.example /tmp/.dbt/profiles.yml
	@echo "Test environment ready"

# CI/CD simulation
ci-test: clean setup-test-env
	@echo "Running CI/CD test simulation..."
	$(MAKE) format-check
	$(MAKE) lint
	$(MAKE) type-check
	$(MAKE) test-coverage
	$(MAKE) validate-suite
	@echo "CI/CD simulation completed successfully"

# Performance monitoring
benchmark:
	pytest tests/ -m "performance" \
		--benchmark-only \
		--benchmark-sort=mean \
		--benchmark-json=benchmark_results.json

# Test specific components
test-infrastructure:
	pytest tests/infrastructure/ -v

test-database:
	pytest tests/database/ -v

test-memory:
	pytest tests/memory/ -v

test-consolidation:
	pytest tests/consolidation/ -v

test-analytics:
	pytest tests/analytics/ -v

test-macros:
	pytest tests/macros/ -v

test-orchestration:
	pytest tests/orchestration/ -v

# Generate reports
report-coverage:
	pytest tests/ --cov=src --cov=models --cov=macros --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

report-performance:
	$(MAKE) benchmark
	@echo "Performance report generated in benchmark_results.json"

# Development helpers
watch-tests:
	pytest-watch tests/ -- -v --tb=short

debug-test:
	pytest tests/ -v -s --tb=long --pdb

# Test suite health check
health-check:
	@echo "Running test suite health check..."
	$(MAKE) validate-suite
	@echo "✅ Test suite structure validated"
	
	@echo "Checking test naming conventions..."
	@find tests/ -name "*.py" -not -name "conftest.py" -not -name "__init__.py" | \
		grep -v "_test.py$$" | grep -v "^test_" && \
		echo "❌ Found files not following _test.py convention" || \
		echo "✅ Test naming convention verified"
	
	@echo "Checking test coverage configuration..."
	@grep -q "cov-fail-under=90" pytest.ini && \
		echo "✅ 90% coverage threshold configured" || \
		echo "❌ Coverage threshold not properly configured"
	
	@echo "Test suite health check completed"

# Documentation generation (when implemented)
docs-tests:
	@echo "Test documentation would be generated here"

# Docker test environment (when implemented)  
docker-test:
	@echo "Docker test environment would be set up here"