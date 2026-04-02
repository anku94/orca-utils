import matplotlib.pyplot as plt
from trace_data import TraceData, get_rundir

import panel as pn


def plot_kokkos_piechart(run_dir: str, top_n: int = 10) -> pn.pane.Matplotlib:
    tr = TraceData(run_dir)
    kokkos_events = tr.read_entire_trace("kokkos_events")
    counts = kokkos_events.group_by("name").len().sort(by="len", descending=True)

    # Top N + Other
    top_kernels = counts.head(top_n)
    other_count = counts.tail(-top_n)["len"].sum() if len(counts) > top_n else 0

    labels = list(top_kernels["name"])
    sizes = list(top_kernels["len"])

    if other_count > 0:
        labels.append("Other")
        sizes.append(other_count)

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=230)

    ax.set_title("Kokkos Events by Kernel Name")

    fig.tight_layout()
    plt.close(fig)

    return pn.pane.Matplotlib(fig, dpi=300, height=700, format='svg', tight=True)



def plot_mpimsg_piechart(run_dir: str, top_n: int = 10) -> pn.pane.Matplotlib:
    tr = TraceData(run_dir)
    mpi_messages = tr.read_entire_trace("mpi_messages")
    counts = mpi_messages.group_by("probe_name").len().sort(by="len", descending=True)

    # Top N + Other
    top_probes = counts.head(top_n)
    other_count = counts.tail(-top_n)["len"].sum() if len(counts) > top_n else 0

    labels = list(top_probes["probe_name"])
    sizes = list(top_probes["len"])

    if other_count > 0:
        labels.append("Other")
        sizes.append(other_count)

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=180)

    ax.set_title("MPI Messages by Probe Name")

    fig.tight_layout()
    plt.close(fig)

    return pn.pane.Matplotlib(fig, dpi=300, height=700, format='svg', tight=True)


def run():
    pn.extension()
    pn.panel("Hello World").servable()

    run_dir = get_rundir(4)

    #plot_kokkos_piechart(run_dir)
    msg_pane = plot_mpimsg_piechart(run_dir)
    kokkos_pane = plot_kokkos_piechart(run_dir)
    pn.Row(msg_pane, kokkos_pane).servable()
    pass

run()


if __name__ == "__main__":
    run()
