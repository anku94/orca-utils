.PHONY: dev replay

HOST ?= localhost
PORT ?= 8989
REPLAY_FILE ?= ./replay.txt

dev:
	echo "Running DashboardApp with host $(HOST) and port $(PORT)"
	textual run --dev interface:DashboardApp -- --host $(HOST) --port $(PORT)

webdev:
	echo "Running DashboardApp with host $(HOST) and port $(PORT)"
	textual serve --dev "python -m interface.dashboard_app --replay $(REPLAY_FILE)"

replay:
	echo "Running DashboardApp with replay file $(REPLAY_FILE)"
	textual run --dev interface:DashboardApp -- --replay $(REPLAY_FILE)

serve:
	echo "Running DashboardApp with replay file $(REPLAY_FILE)"
	textual serve --dev interface:DashboardApp -- --replay $(REPLAY_FILE)

console:
	textual console
