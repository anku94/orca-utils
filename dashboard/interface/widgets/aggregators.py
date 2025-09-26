from textual.app import ComposeResult
from textual.widgets import DataTable, Static

from ..state_manager import StateManager
from ..models import Aggregator
import numpy as np

class AggregatorsWidget(Static):
    """Widget showing aggregator status"""
    
    def __init__(self, state_manager: StateManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_manager = state_manager
        self.table = DataTable()
    
    def compose(self) -> ComposeResult:
        self.border_title = "Aggregators"
        self.table.add_columns("Aggregator", "Range", "Bitset")
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
            ranks_bitmask = self._get_ranks_bitmask(agg)

            self.table.add_row(
                agg_id,
                ranks_str,
                ranks_bitmask
            )

    def _get_ranks_bitmask(self, agg: Aggregator) -> str:
        """Get the bitmask for the ranks in the aggregator"""
        nranks = agg.rank_range[1] - agg.rank_range[0]

        ranks = np.zeros(nranks)
        for rep in agg.reps:
            ranks[rep[1]:rep[2]] = 1

        # Convert to binary string without spaces first
        binary_str = "".join([str(int(rank)) for rank in ranks])
        
        # Group into chunks of 8 bits with spaces between groups
        groups = [binary_str[i:i+8] for i in range(0, len(binary_str), 8)]
        return " ".join(groups)