from textual.app import ComposeResult
from textual.widgets import DataTable, Static

from ..state_manager import StateManager

class AggregatorsWidget(Static):
    """Widget showing aggregator status"""
    
    def __init__(self, state_manager: StateManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_manager = state_manager
        self.table = DataTable()
    
    def compose(self) -> ComposeResult:
        self.border_title = "Aggregators"
        self.table.add_columns("Aggregator", "Ranks")
        yield self.table
    
    def on_mount(self):
        self.state_manager.listen("aggregators", self.update_display)
        self.update_display()
    
    def update_display(self):
        # Clear and rebuild table
        self.table.clear()
        aggregators = self.state_manager.aggregators
        print("Aggregators: ", aggregators)
        
        for agg_id, agg in sorted(self.state_manager.aggregators.items()):
            rbeg, rend = agg.rank_range
            nranks = rend - rbeg
            ranks_str = f"({nranks} ranks) [{rbeg}-{rend})" if nranks > 0 else "empty"
            self.table.add_row(
                agg_id,
                ranks_str
            )
