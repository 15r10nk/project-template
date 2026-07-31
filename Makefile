
.PHONY: test publish

test:
	uvx --from copier-template-tester ctt

publish:
	@test -z "$$(git status --porcelain)" || (echo "Working tree is not clean" >&2; exit 1)
	@next_version="$$(uvx --from commitizen cz bump --get-next)" && \
	uvx --from commitizen cz bump --yes && \
	git push --atomic origin HEAD "v$$next_version"
