BET-MAKER=bet_maker
LINE-PROVIDER=line_provider
export PYTHONPATH := $(PWD):$(PWD)/$(BET-MAKER):$(PWD)/$(LINE-PROVIDER)

# Targets
.PHONY: lint
lint:
	isort $(BET-MAKER)/
	black $(BET-MAKER)/
	ruff check --fix $(BET-MAKER)/
	mypy $(BET-MAKER)/ --check-untyped-defs
	isort $(LINE-PROVIDER)/
	black $(LINE-PROVIDER)/
	ruff check --fix $(LINE-PROVIDER)/
	mypy $(LINE-PROVIDER)/ --check-untyped-defs

.PHONY: clean
clean:
	rm -rf $(BET-MAKER)/__pycache__
	rm -rf $(BET-MAKER)/*.egg-info
	rm -rf $(BET-MAKER)/.pytest_cache
	rm -rf $(BET-MAKER)/.mypy_cache
	rm -rf $(BET-MAKER)/.ruff_cache

.PHONY: paths
paths:
	@echo $(PYTHONPATH)

.PHONY: test
test:
	export PYTHONPATH=$(PWD)/$(BET-MAKER); \
	python -m pytest $(BET-MAKER)/tests/ -vv
	export PYTHONPATH=$(PWD)/$(LINE-PROVIDER); \
	python -m pytest $(LINE-PROVIDER)/tests/ -vv

.PHONY: up
up:
	@$(MAKE) -s down
	@$(MAKE) -s lint
	@$(MAKE) -s test
	@sudo docker-compose up --remove-orphans --build

.PHONY: down
down:
	@sudo docker-compose down

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  up      - Start the services"
	@echo "  down    - Stop the services"
	@echo "  lint    - Run code linters and checkers"
	@echo "  test    - Run all tests"
	@echo "  clean   - Remove build artifacts and temporary files"
	@echo "  paths   - Display python paths"
	@echo "  help    - Show this help message"
