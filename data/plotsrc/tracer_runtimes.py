import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import common as c
from pathlib import Path
from dataclasses import dataclass


@dataclass
class PlotParams:
    xlabel: str
    bar_color: str


PARAM_MAP: dict[str, PlotParams] = {
    "00_noorca": PlotParams(xlabel="Baseline", bar_color="C2"),
    "05_or_trace_mpisync": PlotParams(xlabel="ORCA", bar_color="C1"),
    "07_or_tracetgt": PlotParams(xlabel="ORCA", bar_color="C3"),
    "10_tau_tracetgt": PlotParams(xlabel="TAU", bar_color="C3"),
    "11_dftracer": PlotParams(xlabel="DFTracer", bar_color="C3"),
    # red color for scorep and caliper text in latex syntax
    "13_scorep": PlotParams(xlabel="ScoreP*", bar_color="C3"),
    "17_caliper_tracetgt": PlotParams(xlabel="Caliper*", bar_color="C3"),
}


def get_plotsrc_dir() -> Path:
    try:
        return Path(__file__).parent
    except NameError:
        return Path.cwd()


def fmt_overhead(x: float) -> str:
    # x = x + 100
    if x < 10:
        xval = f"{x:.1f}"
    else:
        xval = f"{x:.0f}"
    return f"\\sffamily\\bfseries +{xval}\%"


def darken_rgba(
    rgba: tuple[float, float, float, float], f: float
) -> tuple[float, float, float, float]:
    return (rgba[0] * f, rgba[1] * f, rgba[2] * f, rgba[3])


def set_bar_hatch(bars: list[mpl.patches.Patch], hatch: str):
    for bar in bars:
        bar.set_hatch(hatch)
        face_rgba = bar.get_facecolor()
        # bar._hatch_color = mpl.colors.to_rgba("#bbb")
        bar._hatch_color = darken_rgba(face_rgba, 0.5)
        bar.stale = True


def fill_baseline(df: pd.DataFrame, baseline: str) -> pd.DataFrame:
    """Fill time_secs_base and ratio columns using the specified baseline profile."""
    df = df.copy()
    base_df = df[df["profile"] == baseline][
        ["ranks", "aggs", "run_id", "steps", "time_secs"]
    ]
    base_df = base_df.rename(columns={"time_secs": "time_secs_base"})
    df = df.drop(columns=["time_secs_base", "ratio"])
    df = df.merge(base_df, on=["ranks", "aggs", "run_id", "steps"], how="left")
    df["ratio"] = df["time_secs"] / df["time_secs_base"]
    return df


def prep_runtime_data(rdf: pd.DataFrame, profiles: list[str]) -> pd.DataFrame:
    nsteps = 2000
    stepfilt = rdf["steps"] == nsteps
    profilt = rdf["profile"].isin(profiles)
    rdf = rdf[profilt & stepfilt].copy()
    rdf["profile"] = pd.Categorical(rdf["profile"], categories=profiles, ordered=True)
    rdf_plot = rdf[["ranks", "profile", "time_secs", "time_secs_base", "ratio"]].copy()

    # group by ranks and profile, compute mean and std of time_secs and time_secs_base
    rdf_pltagg = (
        rdf_plot.groupby(["ranks", "profile"])
        .agg(
            {
                "time_secs": ["mean", "std"],
                "time_secs_base": ["mean", "std"],
                "ratio": "mean",
            }
        )
        .reset_index()
    )
    rdf_pltagg.columns = [
        "ranks",
        "profile",
        "tsecs_mean",
        "tsecs_std",
        "tsecs_base_mean",
        "tsecs_base_std",
        "ratio_mean",
    ]

    return rdf_pltagg


def prep_and_extrapolate() -> pd.DataFrame:
    rdf0_path = c.get_plotdata_dir() / "runtimes" / "20251229.csv"
    rdf0 = pd.read_csv(rdf0_path)
    rdf0_uniq = ",".join(rdf0["profile"].unique().tolist())
    print(f"rdf0_uniq: {rdf0_uniq}")

    print(rdf0)

    rdf0_profiles = [
        c.Prof.BASELINE,
        c.Prof.ORCA_MPISYNC,
        c.Prof.ORCA_TGT,
        c.Prof.TAU_TGT,
        c.Prof.DFTRACER_TGT,
    ]
    r0_pfilt = rdf0["profile"].isin(rdf0_profiles)
    r0_sfilt = rdf0["steps"] == 2000
    rdf0 = rdf0[r0_pfilt & r0_sfilt]

    # Get baseline data to merge with rdf1
    rdf0_base = rdf0[rdf0["profile"] == "00_noorca"]
    rdf0_base = rdf0_base[["ranks", "aggs", "run_id", "time_secs"]]

    rdf1_path = c.get_plotdata_dir() / "runtimes" / "20260106.csv"
    rdf1 = pd.read_csv(rdf1_path)
    rdf1_uniq = ",".join(rdf1["profile"].unique().tolist())
    print(f"rdf1_uniq: {rdf1_uniq}")

    rdf1_profiles = [
        c.Prof.SCOREP_TGT,
        c.Prof.CALIPER_TGT,
    ]
    r1_pfilt = rdf1["profile"].isin(rdf1_profiles)
    r1_sfilt = rdf1["steps"] == 200
    rdf1 = rdf1[r1_pfilt & r1_sfilt]

    # drop row where profile is 17_caliper_tracetgt, ranks=4096, run_id=3
    # We drop that row because of Lustre filling up. TODO: rerun
    rdf1_pf = rdf1["profile"] == "17_caliper_tracetgt"
    rdf1_rf = rdf1["ranks"] == 4096
    rdf1_rf = rdf1["run_id"] == 3
    rdf1_filt = ~(rdf1_pf & rdf1_rf & rdf1_rf)
    rdf1 = rdf1[rdf1_filt]

    rdf1 = rdf1.drop(columns=["time_secs_base"])
    rdf1m = rdf1.merge(
        rdf0_base,
        on=["ranks", "aggs", "run_id"],
        how="left",
        suffixes=["", "_base"],
        validate="many_to_one",
    )
    rdf1m["time_secs"] = rdf1m["ratio"] * rdf1m["time_secs_base"]

    print(rdf0)

    rdf = pd.concat([rdf0, rdf1m], ignore_index=True)

    all_profiles = rdf0_profiles + rdf1_profiles
    rdf["profile"] = pd.Categorical(
        rdf["profile"], categories=all_profiles, ordered=True
    )
    rdf = rdf.sort_values(by=["profile", "ranks"])

    rdf_plot = rdf[["ranks", "profile", "time_secs", "time_secs_base", "ratio"]].copy()
    print(rdf_plot)

    agg_props = {
        "time_secs": ["mean", "std"],
        "time_secs_base": ["mean", "std"],
        "ratio": "mean",
    }
    rdf_pltagg = rdf_plot.groupby(["ranks", "profile"]).agg(agg_props).reset_index()
    rdf_pltagg.columns = [
        "ranks",
        "profile",
        "tsecs_mean",
        "tsecs_std",
        "tsecs_base_mean",
        "tsecs_base_std",
        "ratio_mean",
    ]
    print(rdf_pltagg)
    return rdf_pltagg


def plot_runtime_inner(ax: plt.Axes, prdf: pd.DataFrame, profiles: list[str]):
    xlabels = [PARAM_MAP[p].xlabel for p in profiles]
    bar_colors = [PARAM_MAP[p].bar_color for p in profiles]

    data_x = np.arange(len(prdf))
    data_y = prdf["tsecs_base_mean"]
    # data_yerr = prdf["time_secs_std"]

    data_yxtra = prdf["tsecs_mean"] - data_y
    data_yxtraerr = prdf["tsecs_std"]

    xtra_pcts = (data_yxtra / data_y) * 100
    xtra_labels = [fmt_overhead(x) for x in xtra_pcts]
    xtra_labels[0] = ""
    xtra_labels[-1] += "\\textrightarrow"

    base_bars = ax.bar(data_x, data_y, ec="black", fc="C1")
    for bar, color in zip(base_bars, bar_colors):
        bar.set_color(color)
        bar.set_edgecolor("black")

    set_bar_hatch([base_bars[1]], "///")
    set_bar_hatch(base_bars[2:], "\\" * 3)

    # cap size for error bars
    xtra_bars = ax.bar(data_x, data_yxtra, bottom=data_y, yerr=data_yxtraerr, edgecolor="black", color="C0", capsize=8, hatch="xxx") # fmt: skip
    set_bar_hatch(xtra_bars, "xxx")  # also sets color etc

    # get fontsize
    fontsz = plt.rcParams["font.size"]
    # rotate bar labels by 90 degrees
    blabs = ax.bar_label( xtra_bars, labels=xtra_labels, label_type="edge", fontsize=fontsz - 2, rotation=90, padding=2, clip_on=False) # fmt: skip
    for bidx, blab in enumerate(blabs):
        # blab.set_rotation(60)
        # blab.set_ha("left")
        # blab.set_va("bottom")
        blab.set_bbox(dict(facecolor="white", ec="none", alpha=0.7, pad=1))

        if bidx == len(blabs) - 1:
            blab.set_annotation_clip(False)
            blab.set_anncoords("data")
            blab.xyann = (6, 450)
            blab.set_bbox(dict(facecolor="white", ec="none", alpha=0.5, pad=1))
        else:
            (x, y) = blab.get_position()
            # blab.set_position((x - 5, y))
            pass

    ax.figure.canvas.draw_idle()  # force update
    ax.set_xticks(data_x)
    ax.set_xticklabels(xlabels, rotation=40, ha="right")

    for label in ax.get_xticklabels():
        if label.get_text().endswith("*"):
            label.set_color(c.SpecialColors.FLAG.value)

    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:.0f}\,s"))
    ax.yaxis.grid(which="minor", color="#ddd")
    ax.yaxis.set_minor_locator(mtick.AutoMinorLocator(5))

    ax.grid(which="major", color="#bbb")
    ax.set_axisbelow(True)
    ax.set_ylim(0, 1200)


def plot_runtime(rdf_pltagg: pd.DataFrame):
    all_nranks = rdf_pltagg["ranks"].unique().tolist()
    profiles = rdf_pltagg["profile"].unique().tolist()

    fig, axes = plt.subplots(1, 4, figsize=(c.TEXTWIDTH, 1.6))
    [ax.clear() for ax in axes]

    for ax, nranks in list(zip(axes, all_nranks)):
        prdf = rdf_pltagg[rdf_pltagg["ranks"] == nranks].copy()
        plot_runtime_inner(ax, prdf, profiles)
        # align title to left
        tfsz = plt.rcParams["axes.titlesize"] - 1
        ax.set_title(f"{nranks} ranks", loc="left", pad=3, fontsize=tfsz)
        # ax.set_xlabel(f"\\sffamily\\bfseries {nranks} ranks")

    # blank yticklabels for all but first
    for ax in axes[1:]:
        ax.set_yticklabels([])

    for ax in axes:
        ax.set_ylim([0, 700])
        # ax.set_ylim([0, 1200])
        ax.yaxis.set_major_locator(mtick.MultipleLocator(200))
        ax.yaxis.set_minor_locator(mtick.MultipleLocator(50))
        ax.tick_params(axis="x", pad=1)
        # update x axis rotation
        for label in ax.get_xticklabels():
            label.set_rotation(25)
            label.set_ha("right")
            label.set_va("top")

    axes[0].set_ylabel(r"\textbf{Runtime}")
    axes[0].tick_params(axis="y", pad=2)

    # produce a custom legend with two items, one for each bar color
    handles = axes[0].patches[:3]
    handles.append(axes[0].patches[8])
    labels = ["No Tracing", "Minimal Tracing", "Detailed Tracing", "Overhead"]
    lbbox = (0.52, 1.01)
    figleg = fig.legend(handles, labels, ncol=4, bbox_to_anchor=lbbox, loc="upper center", framealpha=0.9) # fmt: skip
    # figleg.remove()
    fig.tight_layout(pad=0.2)
    fig.subplots_adjust(wspace=0.05, top=0.75, bottom=0.27)

    # Add extrapolation footnote at bottom right
    fig.text(0.99, 0.02, r"\emph{*extrapolated from 200 timesteps}",
             ha="right", va="bottom", fontsize=plt.rcParams["font.size"] - 2,
             style="italic", color="#555")

    c.save_plot(fig, "amr_tracer_runtimes")
    plt.close("all")


def plot_runtime_2x2(rdf_pltagg: pd.DataFrame):
    all_nranks = rdf_pltagg["ranks"].unique().tolist()
    profiles = rdf_pltagg["profile"].unique().tolist()

    fig, axes = plt.subplots(2, 2, figsize=(0.7 * c.TEXTWIDTH, 2.8))
    axes = axes.flatten()
    [ax.clear() for ax in axes]

    for ax, nranks in list(zip(axes, all_nranks)):
        prdf = rdf_pltagg[rdf_pltagg["ranks"] == nranks].copy()
        plot_runtime_inner(ax, prdf, profiles)
        tfsz = plt.rcParams["axes.titlesize"] - 1
        ax.set_title(f"{nranks} ranks", loc="left", pad=3, fontsize=tfsz)

    # blank yticklabels for right column
    for ax in [axes[1], axes[3]]:
        ax.set_yticklabels([])

    # blank xticklabels for top row
    for ax in [axes[0], axes[1]]:
        ax.set_xticklabels([])

    for ax in axes:
        ax.set_ylim([0, 700])
        ax.yaxis.set_major_locator(mtick.MultipleLocator(200))
        ax.yaxis.set_minor_locator(mtick.MultipleLocator(50))
        ax.tick_params(axis="x", pad=1)
        for label in ax.get_xticklabels():
            label.set_rotation(25)
            label.set_ha("right")
            label.set_va("top")

    axes[0].set_ylabel(r"\textbf{Runtime}")
    axes[2].set_ylabel(r"\textbf{Runtime}")
    axes[0].tick_params(axis="y", pad=2)
    axes[2].tick_params(axis="y", pad=2)

    # produce a custom legend with two items, one for each bar color
    handles = axes[0].patches[:3]
    handles.append(axes[0].patches[8])
    labels = ["No Tracing", "Minimal Tracing", "Detailed Tracing", "Overhead"]
    lbbox = (0.52, 1.01)
    figleg = fig.legend(handles, labels, ncol=4, bbox_to_anchor=lbbox, loc="upper center", framealpha=0.9) # fmt: skip
    fig.tight_layout(pad=0.2)
    fig.subplots_adjust(wspace=0.05, hspace=0.4, top=0.86, bottom=0.16)

    # Add extrapolation footnote at bottom right
    fig.text(0.99, 0.01, r"\emph{*extrapolated from 200 timesteps}",
             ha="right", va="bottom", fontsize=plt.rcParams["font.size"] - 2,
             style="italic", color="#555")

    c.save_plot(fig, "amr_tracer_runtimes_2x2")
    plt.close("all")


def plot_runtime_ofitcp():
    # prototyping a different plot for ofitcp
    rdf_path = c.get_plotdata_dir() / "20260101_ofitcp_runtimes.csv"
    profiles = [
        c.Prof.ORCA_MPISYNC,
        c.Prof.ORCA_TCP_SYNC,
        c.Prof.ORCA_TGT,
        c.Prof.ORCA_TCPTGT,
    ]
    rdf = pd.read_csv(rdf_path)
    rdf_pltagg = prep_runtime_data(rdf, profiles)
    print(rdf_pltagg)
    # drop row 0
    dtx = np.arange(len(rdf_pltagg))
    dtybase = rdf_pltagg["tsecs_base_mean"]
    dtyxtra = rdf_pltagg["tsecs_mean"] - dtybase
    dtyxtra_err = rdf_pltagg["tsecs_std"]

    plt.close("all")
    fig, ax = plt.subplots(1, 1, figsize=(c.COLWIDTH * 0.34, 1.4))
    bwidth = 0.1
    # ax.clear()
    dtx = bwidth * np.array([0, 1, 3, 4])
    base_bars = ax.bar(dtx, dtybase, ec="black", fc="C1", width=bwidth) # fmt: skip
    xtra_bars = ax.bar(dtx, dtyxtra, bottom=dtybase, yerr=dtyxtra_err, ec="black", fc="C0", width=bwidth, capsize=8) # fmt: skip

    bidx_verbs = [0, 2]
    bidx_tcp = [1, 3]
    bidx_tgt = [2, 3]

    for idx in bidx_tgt:
        base_bars[idx].set_color("C3")
        base_bars[idx].set_edgecolor("black")

    set_bar_hatch([base_bars[i] for i in bidx_verbs], "///")
    set_bar_hatch([base_bars[i] for i in bidx_tcp], "\\" * 3)
    set_bar_hatch(xtra_bars, "xxx")

    # Darken TCP bars
    for idx in bidx_tcp:
        fc = base_bars[idx].get_facecolor()
        base_bars[idx].set_facecolor(c.darken_hsl(fc, 0.90, 1.1))

    handles = [
        mpatches.Patch(fc="white", ec="black", hatch="////"),
        mpatches.Patch(fc="#ddd", ec="black", hatch="\\" * 4),
        # xtra_bars[0],
    ]
    labels = ["Verbs", "TCP"]  # , "Overhead"]
    bar_labels = (
        rdf_pltagg["ratio_mean"]
        .apply(lambda x: f"\\sffamily\\bfseries +{((x - 1) * 100):.0f}\%")
        .tolist()
    )
    fontsz = plt.rcParams["font.size"]
    blfsz = fontsz - 3
    bbox = dict(facecolor="white", edgecolor="none", alpha=0.5, pad=1)
    ax.bar_label(
        xtra_bars, labels=bar_labels, label_type="edge", fontsize=blfsz, bbox=bbox
    )

    dtx_ticks = (dtx[::2] + dtx[1::2]) / 2
    ax.set_xticks(dtx_ticks)
    xlab = ["Lightweight", "Detailed"]
    mxlab = ax.set_xticklabels(xlab, ha="center")
    ax.set_ylim(0, 520)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:.0f}\,s"))
    ax.text(
        -0.29, 1.02, r"\textbf{Runtime (ORCA)}", transform=ax.transAxes, ha="left", va="bottom"
    )

    ax.yaxis.set_major_locator(mtick.MultipleLocator(100))
    ax.yaxis.set_minor_locator(mtick.AutoMinorLocator(4))
    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", pad=1)
    ax.tick_params(axis="y", pad=1)

    fig.tight_layout(pad=0.3)
    fig.subplots_adjust(top=0.88, bottom=0.29)
    mxlab[0].set_transform(mxlab[0].get_transform() + mpl.transforms.ScaledTranslation(-2/72, 0, fig.dpi_scale_trans))
    lbbox = (0.33, -0.16)
    _ = ax.legend(handles, labels, loc="upper center", fontsize=8, ncols=2, bbox_to_anchor=lbbox, handleheight=0.7, handlelength=1.5) # fmt: skip
    c.save_plot(fig, "ofi_tcp_tracer_runtimes")


def run():
    rdf_pltagg = prep_and_extrapolate()
    # plot_runtime(rdf_pltagg)
    plot_runtime_2x2(rdf_pltagg)
    # plot_runtime_ofitcp()


if __name__ == "__main__":
    plt.style.use(c.get_plotsrc_dir() / "paper.mplstyle")
    c.set_colormap("Pastel1")
    run()
