
.PHONY: test test-act test-ctt publish

test:
	uv run pytest -v

# Requires Docker and gh extension install nektos/gh-act.
test-act:
	uv run pytest tests/test_workflows.py --run-act -v

# Additional generated-project hook checks; rewrites the tracked ctt/ examples.
test-ctt:
	uvx --from copier-template-tester ctt

publish:
	@test -z "$$(git status --porcelain)" || (echo "Working tree is not clean" >&2; exit 1)
	@next_version="$$(uvx --from commitizen cz bump --get-next)" && \
	tag="v$$next_version" && \
	git tag --annotate "$$tag" --message "Release $$tag" && \
	if ! git push --atomic origin HEAD "$$tag"; then \
		git tag --delete "$$tag"; \
		exit 1; \
	fi
