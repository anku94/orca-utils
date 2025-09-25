"""
FlightSQL-specific data query following the Grafana Foundation SDK pattern.
"""

import typing
from grafana_foundation_sdk.cog import variants as cogvariants
from grafana_foundation_sdk.cog import builder as cogbuilder
from grafana_foundation_sdk.models import dashboard
from grafana_foundation_sdk.cog import runtime as cogruntime


class Dataquery(cogvariants.Dataquery):
    """FlightSQL-specific data query model."""
    
    # FlightSQL-specific properties
    query_text: str
    format: typing.Optional[str]
    raw_query: typing.Optional[bool]
    raw_editor: typing.Optional[bool]
    
    # Base DataQuery properties
    ref_id: str
    hide: typing.Optional[bool]
    query_type: typing.Optional[str]
    datasource: typing.Optional[dashboard.DataSourceRef]

    def __init__(self, 
                 query_text: str = "",
                 format: typing.Optional[str] = None,
                 raw_query: typing.Optional[bool] = None,
                 raw_editor: typing.Optional[bool] = None,
                 ref_id: str = "",
                 hide: typing.Optional[bool] = None,
                 query_type: typing.Optional[str] = None,
                 datasource: typing.Optional[dashboard.DataSourceRef] = None):
        self.query_text = query_text
        self.format = format
        self.raw_query = raw_query
        self.raw_editor = raw_editor
        self.ref_id = ref_id
        self.hide = hide
        self.query_type = query_type
        self.datasource = datasource

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "queryText": self.query_text,
            "refId": self.ref_id,
        }
        if self.format is not None:
            payload["format"] = self.format
        if self.raw_query is not None:
            payload["rawQuery"] = self.raw_query
        if self.raw_editor is not None:
            payload["rawEditor"] = self.raw_editor
        if self.hide is not None:
            payload["hide"] = self.hide
        if self.query_type is not None:
            payload["queryType"] = self.query_type
        if self.datasource is not None:
            payload["datasource"] = self.datasource
        return payload

    @classmethod
    def from_json(cls, data: dict[str, typing.Any]) -> typing.Self:
        args: dict[str, typing.Any] = {}
        
        if "queryText" in data:
            args["query_text"] = data["queryText"]
        if "format" in data:
            args["format"] = data["format"]
        if "rawQuery" in data:
            args["raw_query"] = data["rawQuery"]
        if "rawEditor" in data:
            args["raw_editor"] = data["rawEditor"]
        if "refId" in data:
            args["ref_id"] = data["refId"]
        if "hide" in data:
            args["hide"] = data["hide"]
        if "queryType" in data:
            args["query_type"] = data["queryType"]
        if "datasource" in data:
            args["datasource"] = dashboard.DataSourceRef.from_json(data["datasource"])

        return cls(**args)


class DataqueryBuilder(cogbuilder.Builder[Dataquery]):
    """FlightSQL-specific data query builder."""
    
    _internal: Dataquery

    def __init__(self):
        self._internal = Dataquery()

    def build(self) -> Dataquery:
        """Builds the FlightSQL Dataquery object."""
        return self._internal
    
    def query_text(self, query_text: str) -> typing.Self:
        """Sets the FlightSQL query text."""
        self._internal.query_text = query_text
        return self
    
    def format(self, format_val: str) -> typing.Self:
        """Sets the query format (e.g., 'table')."""
        self._internal.format = format_val
        return self
    
    def raw_query(self, raw_query: bool) -> typing.Self:
        """Sets whether to use raw query mode."""
        self._internal.raw_query = raw_query
        return self
    
    def raw_editor(self, raw_editor: bool) -> typing.Self:
        """Sets whether to use raw editor mode."""
        self._internal.raw_editor = raw_editor
        return self
    
    def ref_id(self, ref_id: str) -> typing.Self:
        """Sets the query reference ID."""
        self._internal.ref_id = ref_id
        return self
    
    def hide(self, hide: bool) -> typing.Self:
        """Sets whether to hide the query."""
        self._internal.hide = hide
        return self
    
    def query_type(self, query_type: str) -> typing.Self:
        """Sets the query type."""
        self._internal.query_type = query_type
        return self
    
    def datasource(self, datasource: dashboard.DataSourceRef) -> typing.Self:
        """Sets the datasource reference."""
        self._internal.datasource = datasource
        return self


def variant_config() -> cogruntime.DataqueryConfig:
    """Runtime configuration for FlightSQL dataquery variant."""
    return cogruntime.DataqueryConfig(
        identifier="flightsql",
        from_json_hook=Dataquery.from_json,
    )


# Alias for convenience - this is what should be imported
FsqlDataQuery = DataqueryBuilder
