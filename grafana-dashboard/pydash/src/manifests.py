from grafana_foundation_sdk.models.dashboard import Dashboard
from grafana_foundation_sdk.models.resource import (
    Manifest as SDKManifest,
    Metadata,
)


class Manifest:
    @classmethod
    def dashboard(cls, folder_uid: str, dash: Dashboard) -> SDKManifest:
        if dash.uid is None:
            raise RuntimeError("dashboards must have a uid")

        return SDKManifest(
            api_version="dashboard.grafana.app/v1beta1",
            kind="Dashboard",
            metadata=Metadata(
                annotations={"grafana.app/folder": folder_uid},
                name=dash.uid,
            ),
            spec=dash,
        )
