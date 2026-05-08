.PHONY: help install install-dev test test-verbose demo lint clean package skill-build skill-install git-status

PYTHON := .venv\Scripts\python.exe
UV := uv
PYTEST := .venv\Scripts\pytest.exe

help:
	@echo "Vocalis - Oral Practice Skill"
	@echo ""
	@echo "Available commands:"
	@echo "  make install       - Create venv and install dependencies"
	@echo "  make install-dev   - Install with dev dependencies (pytest, etc.)"
	@echo "  make test          - Run pytest suite"
	@echo "  make test-verbose  - Run pytest with verbose output"
	@echo "  make demo          - Run demo mode (no API calls)"
	@echo "  make demo-charts   - Generate demo charts"
	@echo "  make lint          - Run code checks (ruff)"
	@echo "  make clean         - Remove generated files and caches"
	@echo "  make package       - Build distributable skill package"
	@echo "  make skill-install - Install skill to OpenClaw skills directory"
	@echo "  make skill-build   - Build and package the OpenClaw SKILL"
	@echo "  make git-status    - Show git status"

# Environment setup
install:
	$(UV) venv
	$(UV) pip install -r requirements.txt

install-dev: install
	$(UV) pip install pytest pytest-cov ruff

# Testing
test:
	$(PYTEST) tests/ -v

test-verbose:
	$(PYTEST) tests/ -vv --tb=short

test-cov:
	$(PYTEST) tests/ -v --cov=scripts --cov-report=term-missing --cov-report=html

# Demo
demo:
	$(PYTHON) scripts/main.py --demo

demo-charts:
	$(PYTHON) scripts/generate_mock_history.py
	$(PYTHON) scripts/test_charts.py

# Code quality
lint:
	$(UV) pip install ruff || true
	.venv\Scripts\ruff.exe check scripts/ tests/
	.venv\Scripts\ruff.exe format --check scripts/ tests/

format:
	.venv\Scripts\ruff.exe format scripts/ tests/

# Cleaning
clean:
	@echo "Cleaning generated files..."
	rmdir /s /q scripts\__pycache__ 2>nul || true
	rmdir /s /q tests\__pycache__ 2>nul || true
	rmdir /s /q .pytest_cache 2>nul || true
	rmdir /s /q htmlcov 2>nul || true
	rmdir /s /q dist 2>nul || true
	rmdir /s /q build 2>nul || true
	del /q reports\*.png 2>nul || true
	del /q reports\*.md 2>nul || true
	del /q data\*.json 2>nul || true
	del /q data\*.mp3 2>nul || true
	@echo "Clean complete."

# Skill packaging for OpenClaw
SKILL_NAME := vocalis
SKILL_VERSION := 0.1.0
DIST_DIR := dist
SKILL_DIR := $(DIST_DIR)/$(SKILL_NAME)-$(SKILL_VERSION)

package: clean
	@echo "Building Vocalis skill package..."
	@if not exist "$(DIST_DIR)" mkdir "$(DIST_DIR)"
	@if not exist "$(SKILL_DIR)" mkdir "$(SKILL_DIR)"
	@echo "Copying skill files..."
	xcopy /s /i /y scripts "$(SKILL_DIR)\scripts\" >nul
	xcopy /s /i /y tests "$(SKILL_DIR)\tests\" >nul
	copy config.yaml "$(SKILL_DIR)\" >nul
	copy requirements.txt "$(SKILL_DIR)\" >nul
	copy Makefile "$(SKILL_DIR)\" >nul
	copy README.md "$(SKILL_DIR)\" >nul 2>nul || echo "No README.md, skipping..."
	@echo "Creating SKILL.md..."
	$(PYTHON) scripts\main.py --help > "$(SKILL_DIR)\SKILL.md" 2>nul || echo "# Vocalis Skill" > "$(SKILL_DIR)\SKILL.md"
	@echo "Creating archive..."
	cd "$(DIST_DIR)" && powershell -Command "Compress-Archive -Path '$(SKILL_NAME)-$(SKILL_VERSION)' -DestinationPath '$(SKILL_NAME)-$(SKILL_VERSION).zip' -Force"
	@echo "Package built: $(DIST_DIR)\$(SKILL_NAME)-$(SKILL_VERSION).zip"

skill-build: package
	@echo "Skill build complete."

OPENCLAW_SKILLS_DIR := $(USERPROFILE)\.openclaw\skills

skill-install:
	@echo "Installing Vocalis skill to OpenClaw..."
	@if not exist "$(OPENCLAW_SKILLS_DIR)\$(SKILL_NAME)" mkdir "$(OPENCLAW_SKILLS_DIR)\$(SKILL_NAME)"
	xcopy /s /i /y scripts "$(OPENCLAW_SKILLS_DIR)\$(SKILL_NAME)\scripts\" >nul
	copy config.yaml "$(OPENCLAW_SKILLS_DIR)\$(SKILL_NAME)\" >nul
	copy requirements.txt "$(OPENCLAW_SKILLS_DIR)\$(SKILL_NAME)\" >nul
	@echo "Skill installed to: $(OPENCLAW_SKILLS_DIR)\$(SKILL_NAME)"

# Git
git-status:
	git status

git-commit:
	git add -A
	git commit -m "$(MSG)"
