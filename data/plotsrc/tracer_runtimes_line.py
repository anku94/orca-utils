import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd
import common as c
from tracer_runtimes import prep_and_extrapolate
from query_suite import read_query_suite_data, prep_query_suite_data, plot_query_inner, QUERY_MAP


# Hardcoded label positions (axes coordinates)
# Format: (x, y) where x,y are 0-1 in axes space
LABEL_POSITIONS = {
    c.Prof.ORCA_TGT: (0.48, 0.4),
    c.Prof.TAU_TGT: (0.85, 0.6),
    c.Prof.DFTRACER_TGT: (0.72, 0.82),
    c.Prof.SCOREP_TGT: (0.75, 0.52),
    c.Prof.CALIPER_TGT: (0.42, 0.92),
}


def fmt_overhead(val: float) -> str:
    if val < 10:
        return f"{val:.1f}"
    return f"{val:.0f}"


def get_overhead_str(vals: pd.Series) -> str:
    omin = (vals.min() - 1) * 100
    omax = (vals.max() - 1) * 100
    return f"\\sffamily\\bfseries +{fmt_overhead(omin)}\%--{fmt_overhead(omax)}\%"


def plot_runtime_line_inner(ax: plt.Axes, rdf: pd.DataFrame, bbox_alpha: float = 0.4):
    """Plot runtime line chart on given axes. Reusable for composition."""
    all_nranks = rdf["ranks"].unique().tolist()

    # Filter out baseline and ORCA lightweight
    exclude = [c.Prof.BASELINE, c.Prof.ORCA_MPISYNC]
    # Dashed lines for extrapolated data
    dashed_profiles = [c.Prof.SCOREP_TGT, c.Prof.CALIPER_TGT]
    rdf = rdf[~rdf["profile"].isin(exclude)]
    profiles = rdf["profile"].unique().tolist()

    annotsz = plt.rcParams["font.size"] - 3

    for profile in profiles:
        pdf = rdf[rdf["profile"] == profile]
        data_x = pdf["ranks"]
        data_y = pdf["ratio_mean"]

        pprops = c.PROF_PROPS[c.Prof(profile)]
        is_extrapolated = c.Prof(profile) in dashed_profiles
        linestyle = "--" if is_extrapolated else "-"
        alpha = 0.35 if is_extrapolated else 0.7
        hnd = ax.plot(
            data_x,
            data_y,
            marker=pprops.marker,
            label=pprops.label,
            color=pprops.color,
            mec="black",
            alpha=alpha,
            linestyle=linestyle,
        )

        # Add overhead label
        txy = LABEL_POSITIONS.get(c.Prof(profile))
        if txy is not None:
            overhead_str = get_overhead_str(pdf["ratio_mean"])
            # Special label for Caliper (out of bounds)
            if c.Prof(profile) == c.Prof.CALIPER_TGT:
                overhead_str = f"\\textbf{{Caliper:}} {overhead_str} $\\uparrow$"
            txtcolor = c.darken_rgba(hnd[0].get_color(), 0.6)
            txt_alpha = 0.75 if is_extrapolated else 1.0
            bbox = dict(facecolor="white", ec="none", alpha=bbox_alpha * txt_alpha, pad=1)
            ax.text(txy[0], txy[1], overhead_str, transform=ax.transAxes,
                    ha="center", va="bottom", fontsize=annotsz, color=txtcolor, bbox=bbox, alpha=txt_alpha)

    ax.set_xlabel(r"\textbf{Ranks}")
    ax.set_ylabel(r"\textbf{Relative Runtime}")

    ax.set_xscale("log")
    ax.set_xticks(all_nranks)
    ax.set_xticklabels([f"{x}" for x in all_nranks])
    ax.xaxis.set_minor_formatter(mtick.NullFormatter())
    ax.xaxis.set_minor_locator(mtick.NullLocator())

    ax.set_ylim(0, 2)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x*100:.0f}\%"))
    ax.yaxis.set_major_locator(mtick.MultipleLocator(0.5))
    ax.yaxis.set_minor_locator(mtick.MultipleLocator(0.1))

    ax.grid(which="major", color="#bbb")
    ax.yaxis.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", pad=1)
    ax.tick_params(axis="y", pad=2)


def plot_runtime_line():
    """Standalone runtime line plot with legend."""
    rdf = prep_and_extrapolate()
    c.set_colormap("Pastel1-Dark")

    fig, ax = plt.subplots(1, 1, figsize=(3.0, 1.6))
    plot_runtime_line_inner(ax, rdf)

    lfsz = plt.rcParams["legend.fontsize"] - 1
    legh, legl = ax.get_legend_handles_labels()
    ltoflag = ["Score-P", "Caliper"]
    legl = [f"{l}*" if l in ltoflag else l for l in legl]

    lobj = fig.legend(
        legh,
        legl,
        loc="outside upper center",
        fontsize=lfsz,
        ncols=5,
        handlelength=1.5,
    )
    for l in lobj.get_texts():
        if l.get_text().endswith("*"):
            l.set_color(c.SpecialColors.FLAG.value)

    fig.tight_layout(pad=0.2)
    fig.subplots_adjust(top=0.82)
    c.save_plot(fig, "amr_tracer_runtimes_line")
    plt.close("all")


def plot_runtime_combo():
    """1x2 combo: runtime line + query outlier waits. No legend (for stitching)."""
    # Prep data
    rdf = prep_and_extrapolate()
    qdf_raw = read_query_suite_data()
    qdf = prep_query_suite_data(qdf_raw)
    qdf = qdf[qdf["steps"] == 20]
    qdf = qdf[qdf["query_name"] == "count_mpi_wait_dur"]  # Outlier Waits

    c.set_colormap("Pastel1-Dark")

    fig, axes = plt.subplots(1, 2, figsize=(c.TEXTWIDTH * 0.5, 1.5))

    # Left: runtime line
    plot_runtime_line_inner(axes[0], rdf, bbox_alpha=0.7)
    axes[0].set_xlabel("")  # Clear xlabel, will use shared label

    # Right: query outlier waits
    plot_query_inner(axes[1], qdf.copy())
    axes[1].set_ylim(1.5e-1, 5e4)
    axes[1].yaxis.set_major_locator(mtick.LogLocator(base=10, numticks=5))
    axes[1].yaxis.set_minor_locator(mtick.LogLocator(base=10, subs=[2, 5], numticks=5))
    axes[1].tick_params(axis="both", pad=1)
    axes[1].set_ylabel(r"\textbf{Rel. Query Latency}")
    axes[1].set_xlabel("")  # Clear xlabel, will use shared label

    # Add two-headed arrow showing gap at 4096 ranks
    # Compute ratio for annotation (ORCA=1, find max of others at 4096)
    qdf_4096 = qdf[qdf["nranks"] == 4096].copy()
    orca_ms = qdf_4096[qdf_4096["profile"] == c.Prof.ORCA_TGT]["total_ms_mean"].values[0]
    other_ms = qdf_4096[qdf_4096["profile"] != c.Prof.ORCA_TGT]["total_ms_mean"].max()
    ratio_mag = int(round(other_ms / orca_ms))

    # x=3 is 4096 ranks index, y positions in data coords (log scale)
    x_arrow = 2.8  # Slightly left of 4096 ranks
    y_low = 1.0  # ORCA baseline (ratio=1)
    y_high = other_ms / orca_ms
    arrow_color = "#C45050"  # Muted but visible red
    axes[1].annotate(
        "", xy=(x_arrow, y_high), xytext=(x_arrow, y_low),
        arrowprops=dict(arrowstyle="<->", color=arrow_color, lw=1.2, shrinkA=0, shrinkB=0),
    )
    annotsz = plt.rcParams["font.size"] - 2
    axes[1].text(x_arrow - 0.08, (y_low * y_high) ** 0.5, f"\\textbf{{{ratio_mag}}}$\\times$",
                 ha="right", va="center", fontsize=annotsz, color=arrow_color)

    # "Ranks" label to left of first tick on first axis only
    axes[0].set_xlabel(r"\textbf{Ranks}", ha="right")
    axes[0].xaxis.set_label_coords(-0.07, -0.04)

    fig.tight_layout(pad=0.2)
    fig.subplots_adjust(bottom=0.18)

    # Disclaimer for dashed lines (Score-P, Caliper)
    disc_fsz = plt.rcParams["font.size"] - 3
    fig.text(0.99, 0.02, r"\textit{*Extrapolated from 512--2048 ranks}",
             ha="right", va="bottom", fontsize=disc_fsz, color="#666")
    c.save_plot(fig, "runtime_query_combo")
    plt.close("all")


if __name__ == "__main__":
    plt.style.use(c.get_plotsrc_dir() / "paper.mplstyle")
    c.set_colormap("Pastel1")
    plot_runtime_line()
    plot_runtime_combo()
