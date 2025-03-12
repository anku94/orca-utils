from dataclasses import dataclass
from textual.message import Message

@dataclass
class ClearLogRequest(Message):
    """Message to request clearing the log widget"""
    pass
