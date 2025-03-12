from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import  Static, Button
from textual.widget import Widget
from rich.text import Text

ORCA_STR = """
            ██████╗ ██████╗  ██████╗ █████╗ 
            ██╔═══██╗██╔══██╗██╔════╝██╔══██╗
            ██║   ██║██████╔╝██║     ███████║
            ██║   ██║██╔══██╗██║     ██╔══██║
            ╚██████╔╝██║  ██║╚██████╗██║  ██║
            ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝ 

 [[ OBSERVABILITY WITH REALTIME CONTROL AND AGGREGATION ]]

                  PRESS 'O' TO CONTINUE
"""

class Orca(Container):
    def __init__(self, *args, **kwargs):
        super().__init__(
            id="orca-container",
            *args, **kwargs)

    def compose(self) -> ComposeResult:
        yield Static(content=Text(ORCA_STR), id="orca-text")
        yield Button(id="orca-close")

    def on_mount(self) -> None:
        pass