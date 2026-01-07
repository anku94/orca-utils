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
        cycle, wsec_total, wsec_step = int(
            cycle), float(wsec_total), float(wsec_step)
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


def process_cycle_log(log_file: str) -> pd.DataFrame:
    df = parse_cycle_log(log_file)
    df = df[df["cycle"] > 0]
    df = df.set_index("cycle")
    return df


def plot_steps(df_a: pd.DataFrame, df_b: pd.DataFrame) -> pn.pane.Matplotlib:
    fig, ax = plt.subplots(1, 1, figsize=(4, 3))

    ax.plot(df_a.index, df_a["wsec_step"], label="Without ORCA")
    ax.plot(df_b.index, df_b["wsec_step"], label="With ORCA")

    ax.set_xlim(left=1)
    # multiply y by 1000 and call it ms
    ax.yaxis.set_major_formatter(
        mtick.FuncFormatter(lambda x, _: f"{x*1000:.0f} ms"))
    ax.set_ylim(0, 0.400)
    ax.grid(which='major', color='#bbb')
    ax.grid(which='minor', color='#bbb')
    ax.yaxis.set_minor_locator(mtick.AutoMinorLocator(4))
    plt.close(fig)

    return pn.pane.Matplotlib(fig, width=600, dpi=144, format='svg', tight=True)


def run():
    pn.extension()
    pn.panel("Hello World").servable()

    suite_dir = "/mnt/ltio/orcajobs/suites/20251227"
    log0 = f"{suite_dir}/amr-agg4-r4096-n2000-run1/00_noorca/mpi.log"
    log1 = f"{suite_dir}/amr-agg4-r4096-n2000-run1/05_or_trace_mpisync/mpi.log"
    log2 = f"{suite_dir}/amr-agg4-r4096-n2000-run2/05_or_trace_mpisync/mpi.log"
    log3 = f"{suite_dir}/amr-agg4-r4096-n2000-run3/05_or_trace_mpisync/mpi.log"

    df0 = process_cycle_log(log0)
    df1 = process_cycle_log(log1)
    df2 = process_cycle_log(log2)
    df3 = process_cycle_log(log3)
    # p0 = pn.pane.DataFrame(df0, width=400, name="Without ORCA")
    # p1 = pn.pane.DataFrame(df2, width=400, name="With ORCA")
    # diffs = df2["wsec_step"] - df0["wsec_step"]

    # plot_steps(df0, df2).servable()

    fig, ax = plt.subplots(1, 1, figsize=(6, 3))
    ax.plot(df0.index, df0["wsec_step"].cumsum(), label="Without ORCA")
    ax.plot(df1.index, df1["wsec_step"].cumsum(), label="With ORCA")
    ax.plot(df2.index, df2["wsec_step"].cumsum(), label="With ORCA")
    ax.plot(df3.index, df3["wsec_step"].cumsum(), label="With ORCA")
    ax.legend()
    ax.grid(which='major', color='#bbb')
    ax.grid(which='minor', color='#bbb')
    ax.yaxis.set_minor_locator(mtick.AutoMinorLocator(4))
    cumsum_plot = pn.pane.Matplotlib(fig, width=800, format='svg', tight=True)
    pn.Row(cumsum_plot).servable()

    pn.Row(df0, df1, df2, df3).servable()

    # df2 cycle >= 9
    # df2 = df2[df2["cycle"] >= 9]

    # make cycle the index of df0
    df0 = df0.set_index("cycle")
    df2 = df2.set_index("cycle")

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
