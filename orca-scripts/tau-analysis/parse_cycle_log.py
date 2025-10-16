import re
import pandas as pd

import panel as pn

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

import numpy as np


def parse_cycle_log(log_file: str) -> pd.DataFrame:
    """Parse cycle lines and extract wsec_total and wsec_step."""

    records = []

    lines = open(log_file).readlines()
    lines = [l for l in lines if l.startswith("cycle")]

    regex = r"cycle=(\d+).*wsec_total=([0-9.e\-\+]+).*wsec_step=([0-9.e\-\+]+)"
    for l in lines:
        mobj = re.search(regex, l)
        assert mobj is not None, f"Failed to parse line: {l}"
        cycle, wsec_total, wsec_step = mobj.groups()
        cycle, wsec_total, wsec_step = int(cycle), float(wsec_total), float(wsec_step)
        records.append(
            {
                "cycle": cycle,
                "wsec_total": wsec_total,
                "wsec_step": wsec_step,
            }
        )

    df = pd.DataFrame(records)
    print(df)

    return pd.DataFrame(records)


def plot_steps(df_a: pd.DataFrame, df_b: pd.DataFrame) -> pn.pane.Matplotlib:
    fig, ax = plt.subplots(1, 1, figsize=(4, 3))

    ax.plot(df_a["cycle"], df_a["wsec_step"], label="Without ORCA")
    ax.plot(df_b["cycle"], df_b["wsec_step"], label="With ORCA")

    ax.set_xlim(left=1)
    # multiply y by 1000 and call it ms
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x*1000:.0f} ms"))
    ax.set_ylim(0, 0.400)
    ax.grid(which='major', color='#bbb')
    ax.grid(which='minor', color='#bbb')
    ax.yaxis.set_minor_locator(mtick.AutoMinorLocator(4))
    plt.close(fig)

    return pn.pane.Matplotlib(fig, dpi=144, format='svg', tight=True)

def run():
    pn.extension()
    pn.panel("Hello World").servable()

    log0 = "/mnt/ltio/orcajobs/run1/mpirun.log"
    log_file = log0
    df0 = parse_cycle_log(log0)

    log2 = "/mnt/ltio/orcajobs/run0/mpirun.log"
    df2 = parse_cycle_log(log2)

    plot_steps(df0, df2).servable()
    # df2 cycle >= 9
    df2 = df2[df2["cycle"] >= 9]

    # make cycle the index of df0
    df0 = df0.set_index("cycle")
    df2 = df2.set_index("cycle")

    pane0 = pn.pane.DataFrame(df0, width=400, name="Without ORCA")
    pane2 = pn.pane.DataFrame(df2, width=400, name="With ORCA")

    steps0 = df0["wsec_step"]
    steps2 = df2["wsec_step"]
    diffs = steps2 - steps0

    # plot a histogram of diffs
    fig, ax = plt.subplots(1, 1, figsize=(6, 3))
    ax.hist(diffs * 1000, bins=40)
    ax.set_xlabel("Difference in wsec_step (With ORCA - Without ORCA)")
    ax.set_ylabel("Number of cycles")
    ax.grid(which='major', color='#bbb')
    ax.grid(which='minor', color='#bbb')
    ax.yaxis.set_minor_locator(mtick.AutoMinorLocator(4))
    ax.set_axisbelow(True)
    plt.close(fig)
    diff_plot = pn.pane.Matplotlib(fig, dpi=144, format='svg', tight=True)

    diff_plot.servable()
    pn.Row(pane0, pane2, diffs).servable()


if __name__ == "__main__":
    # Hardcoded path
    run()


run()
