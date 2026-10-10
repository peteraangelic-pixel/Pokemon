# ARC-AGI-3 local development and deployment commands.
# Source of truth: agent/*.py. Generated data, vendor code, credentials and
# notebooks are ignored by Git.

PYTHON             ?= python3.12
VENV               := .venv
VENV_PY            := $(VENV)/bin/python
VENV_PIP           := $(VENV)/bin/pip
FRAMEWORK_REPO     := https://github.com/arcprize/ARC-AGI-3-Agents.git
FRAMEWORK_DIR      := vendor/ARC-AGI-3-Agents
ACCELERATOR        ?= cpu
GAME               ?= ls20,vc33
STEPS              ?= 120
EVAL_STEPS         ?= 400
KAGGLE             := KAGGLE_API_TOKEN=$$(cat .kaggle/access_token) $(VENV)/bin/kaggle

.PHONY: help configure-kaggle setup test list-games play-local verify-local evaluate-public notebook submit status clean

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Variables: PYTHON=$(PYTHON) GAME=$(GAME) STEPS=$(STEPS) EVAL_STEPS=$(EVAL_STEPS) ACCELERATOR=$(ACCELERATOR)"

configure-kaggle: ## Copy ignored ../kaggle.json into ignored .kaggle/access_token
	$(PYTHON) scripts/configure_kaggle.py

setup: ## Create Python 3.12 venv, install ARC SDK and clone reference framework
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install "arc-agi>=0.9.6" "kaggle>=2.2" "pydantic>=2" "python-dotenv>=1" "requests>=2"
	@if [ ! -d "$(FRAMEWORK_DIR)/.git" ]; then \
		mkdir -p vendor && git clone --depth 1 $(FRAMEWORK_REPO) $(FRAMEWORK_DIR); \
	else \
		git -C $(FRAMEWORK_DIR) pull --ff-only; \
	fi
	$(VENV_PY) scripts/prepare_framework.py
	@echo "Setup complete. Next: make test && make verify-local"

test: ## Run SDK-free unit tests (no network, model, or credential needed)
	$(PYTHON) -m unittest discover -s tests -v

list-games: ## List environments visible to the local ARC SDK
	$(VENV_PY) scripts/play_local.py --list

play-local: ## Play selected public games locally; GAME=ls20,vc33 STEPS=120
	$(VENV_PY) scripts/play_local.py --game "$(GAME)" --max-steps $(STEPS) --record

verify-local: ## Short smoke run on ls20 and vc33; writes recordings/local-smoke-report.json
	$(VENV_PY) scripts/play_local.py --game ls20,vc33 --max-steps 50 --record --report recordings/local-smoke-report.json

evaluate-public: ## Bounded graph evaluation; GAME=ls20,vc33 EVAL_STEPS=400
	$(VENV_PY) scripts/play_local.py --game "$(GAME)" --max-steps $(EVAL_STEPS) --record --report recordings/public-eval-report.json

notebook: ## Generate ignored notebooks/submission.ipynb; ACCELERATOR=cpu|t4|p100|rtx6000
	$(VENV_PY) scripts/build_notebook.py --accelerator $(ACCELERATOR)

submit: notebook ## Push notebook for Kaggle Save & Run All (not an official leaderboard entry)
	@test -s .kaggle/access_token || { echo "Missing .kaggle/access_token; run make configure-kaggle"; exit 1; }
	$(KAGGLE) kernels push -p notebooks
	@echo "Notebook pushed. Inspect its Kaggle run before selecting an official competition submission."

status: ## Show most recent Kaggle notebook execution state
	@test -s .kaggle/access_token || { echo "Missing .kaggle/access_token; run make configure-kaggle"; exit 1; }
	@KERNEL_ID=$$($(VENV_PY) -c "import json; print(json.load(open('notebooks/kernel-metadata.json'))['id'])"); \
	$(KAGGLE) kernels status $$KERNEL_ID

clean: ## Delete ignored/generated local ARC artifacts
	rm -rf $(VENV) .kaggle vendor environment_files recordings notebooks/submission.ipynb __pycache__ agent/__pycache__ scripts/__pycache__ tests/__pycache__
