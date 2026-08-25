.POSIX:

# Test entry point (family decision 4, issue #59). Wraps the existing
# checks — the scripts themselves are canonical; do not add logic here.
test:
	bash tools/selftest_repo_state_gen.sh
	python3 -B tools/selftest_check_registry.py
	python3 -B tools/selftest_family_footer.py
	python3 -B tools/check_publication_gate.py --selftest
	python3 -B tools/selftest_check_evidence_warning.py
	python3 -B tools/check_registry.py --offline
	python3 -B tools/render.py --check

# No lint tooling exists in this repo yet (stdlib-only python, no config).
# Kept as an explicit no-op so `make lint` is a stable entry point for CI.
lint:
	@echo "lint: no lint tooling configured for this repo (no-op)"

.PHONY: test lint
