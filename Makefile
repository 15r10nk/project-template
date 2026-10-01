
.PHONY: test publish

test:
	uv run --no-project --with "copier>=9.10,<10" python -m unittest discover -s tests
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
