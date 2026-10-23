.PHONY: validate hassfest hacs

REPO ?= dvdvnl/ha-open_data_bz_meteo

validate: hassfest hacs

hassfest:
	docker run --rm -v "$(CURDIR)":/github/workspace ghcr.io/home-assistant/hassfest

hacs:
	docker run --rm \
		-e INPUT_CATEGORY=integration \
		-e INPUT_GITHUB_TOKEN="$(GITHUB_TOKEN)" \
		-e GITHUB_REPOSITORY=$(REPO) \
		-e GITHUB_WORKSPACE=/github/workspace \
		-v "$(CURDIR)":/github/workspace \
		ghcr.io/hacs/action:main

docker-up:
	docker-compose up -d --force-recreate --remove-orphans && docker compose logs -f

docker-down:
	docker-compose down --remove-orphans
