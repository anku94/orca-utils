import urllib.parse
import json
import os
import typing
import requests
from grafana_foundation_sdk.models.dashboard import Dashboard
from grafana_foundation_sdk.cog.encoder import JSONEncoder


class Config:
    host: str
    user: str
    password: str

    def __init__(self, host: str = "", user: str = "", password: str = ""):
        self.host = host
        self.user = user
        self.password = password

    @classmethod
    def from_env(cls) -> typing.Self:
        return cls(
            host=os.environ.get("GRAFANA_HOST", "localhost:3000"),
            user=os.environ.get("GRAFANA_USER", "admin"),
            password=os.environ.get("GRAFANA_PASSWORD", "admin"),
        )


class Client:
    config: Config

    def __init__(self, config: Config):
        self.config = config

    def find_or_create_folder(self, name: str) -> str:
        auth = (self.config.user, self.config.password)
        response = requests.get(
            f"http://{self.config.host}/api/search?type=dash-folder&query={urllib.parse.quote_plus(name)}",
            auth=auth,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"could not fetch folders list: expected 200, got {response.status_code}"
            )

        # The folder exists.
        response_json = response.json()
        if len(response_json) == 1:
            return response_json[0]["uid"]

        # The folder doesn't exist: we create it.
        response = requests.post(
            f"http://{self.config.host}/api/folders",
            auth=auth,
            headers={"Content-Type": "application/json"},
            data=json.dumps({"title": name}),
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"could not create new folder: expected 200, got {response.status_code}"
            )

        return response.json()["uid"]

    def persist_dashboard(self, dashboard: Dashboard):
        auth = (self.config.user, self.config.password)
        response = requests.post(
            f"http://{self.config.host}/api/dashboards/db",
            auth=auth,
            headers={"Content-Type": "application/json"},
            data=json.dumps(
                {
                    "dashboard": dashboard,
                    #"folderUid": "orca",
                    "overwrite": True,
                },
                cls=JSONEncoder,
            ),
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"could not persist dashboard: expected 200, got {response.status_code}"
            )

    def find_datasource_by_name(self, name: str) -> typing.Optional[dict]:
        """Find a datasource by name. Returns the datasource dict or None if not found."""
        auth = (self.config.user, self.config.password)
        response = requests.get(
            f"http://{self.config.host}/api/datasources",
            auth=auth,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"could not fetch datasources list: expected 200, got {response.status_code}"
            )

        datasources = response.json()
        for ds in datasources:
            if ds.get("name") == name:
                return ds
        return None

    def find_datasource_by_uid(self, uid: str) -> typing.Optional[dict]:
        """Find a datasource by UID. Returns the datasource dict or None if not found."""
        auth = (self.config.user, self.config.password)
        response = requests.get(
            f"http://{self.config.host}/api/datasources/uid/{uid}",
            auth=auth,
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            raise RuntimeError(
                f"could not fetch datasource by uid: expected 200 or 404, got {response.status_code}"
            )

    def create_or_update_datasource(self, datasource_config: dict) -> dict:
        """Create a new datasource or update an existing one by name."""
        auth = (self.config.user, self.config.password)
        
        # Check if datasource already exists
        existing_ds = self.find_datasource_by_name(datasource_config.get("name", ""))
        
        if existing_ds:
            # Update existing datasource
            datasource_id = existing_ds["id"]
            # Preserve the ID and version for updates
            update_config = {**datasource_config, "id": datasource_id}
            if "version" in existing_ds:
                update_config["version"] = existing_ds["version"]
                
            response = requests.put(
                f"http://{self.config.host}/api/datasources/{datasource_id}",
                auth=auth,
                headers={"Content-Type": "application/json"},
                data=json.dumps(update_config),
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"could not update datasource: expected 200, got {response.status_code}, response: {response.text}"
                )
        else:
            # Create new datasource
            response = requests.post(
                f"http://{self.config.host}/api/datasources",
                auth=auth,
                headers={"Content-Type": "application/json"},
                data=json.dumps(datasource_config),
            )
            if response.status_code not in [200, 201]:
                raise RuntimeError(
                    f"could not create datasource: expected 200 or 201, got {response.status_code}, response: {response.text}"
                )

        return response.json()

    def delete_datasource(self, name: str) -> bool:
        """Delete a datasource by name. Returns True if deleted, False if not found."""
        auth = (self.config.user, self.config.password)
        
        # Find datasource by name first
        existing_ds = self.find_datasource_by_name(name)
        if not existing_ds:
            return False
            
        response = requests.delete(
            f"http://{self.config.host}/api/datasources/{existing_ds['id']}", 
            auth=auth
        )
        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        else:
            raise RuntimeError(
                f"could not delete datasource: expected 200 or 404, got {response.status_code}, response: {response.text}"
            )
