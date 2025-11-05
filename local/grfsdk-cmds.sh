# Install the Python Foundation SDK
pysdk_url="https://github.com/grafana/grafana-foundation-sdk"
pysdk_branch="v11.6.x+cog-v0.0.x"
pysdk_pip="git+${pysdk_url}@${pysdk_branch}#subdirectory=python"
echo "Installing $pysdk_pip ..."
pip install $pysdk_pip
# pip uninstall -y grafana-foundation-sdk  # in case it was installed before

# Install the Grafana CLI
go install github.com/grafana/grafanactl/cmd/grafanactl@latest

alias grafanactl=/Users/schwifty/go/bin/grafanactl

# https://grafana.com/docs/grafana/latest/observability-as-code/grafana-cli/set-up-grafana-cli/
# https://grafana.github.io/grafanactl/configuration/
grafanactl config set contexts.default.grafana.server http://localhost:3000
grafanactl config set contexts.default.grafana.org-id 1
grafanactl config set contexts.default.grafana.user admin
grafanactl config set contexts.default.grafana.password admin
grafanactl config check

ORCAUTILS_DIR=/Users/schwifty/Repos/mon-repos/orca-utils
PY_SCRIPT="$ORCAUTILS_DIR/grafana-dashboard/pydash/metrics_dashboard.py"

grafanactl resources


grafanactl resources --verbose serve --script "python $PY_SCRIPT"

grafanactl resources serve \
  --script 'python /Users/schwifty/Repos/mon-repos/orca-utils/grafana-dashboard/pydash/metrics_dashboard.py' \
  --watch '/Users/schwifty/Repos/mon-repos/orca-utils/grafana-dashboard/pydash'
