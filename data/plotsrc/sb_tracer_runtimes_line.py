import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import common as c
from tracer_runtimes import prep_and_extrapolate
from tracer_runtimes_line import get_overhead_str

LABEL_POSITIONS = {
    c.Prof.ORCA_TGT: (0.48, 0.05),
    c.Prof.TAU_TGT: (0.75, 0.44),
    c.Prof.DFTRACER_TGT: (0.68, 0.62),
    c.Prof.SCOREP_TGT: (0.75, 0.18),
    c.Prof.CALIPER_TGT: (0.42, 0.93),
}


def plot_runtime_line_inner(ax: plt.Axes, rdf, bbox_alpha: float = 0.4):
    all_nranks = rdf["ranks"].unique().tolist()

    exclude = [c.Prof.BASELINE, c.Prof.ORCA_MPISYNC]
    dashed_profiles = [c.Prof.SCOREP_TGT, c.Prof.CALIPER_TGT]
    rdf = rdf[~rdf["profile"].isin(exclude)]
    profiles = rdf["profile"].unique().tolist()

    # Baseline: horizontal line at y=1.0
    ax.axhline(y=1.0, color="#888888", linestyle="-", linewidth=1.5, label="Baseline", zorder=1)

    annotsz = plt.rcParams["font.size"] - 1

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

        txy = LABEL_POSITIONS.get(c.Prof(profile))
        if txy is not None:
            overhead_str = get_overhead_str(pdf["ratio_mean"])
            if c.Prof(profile) == c.Prof.CALIPER_TGT:
                overhead_str = f"\\textbf{{Caliper:}} {overhead_str} $\\uparrow$"
            txtcolor = c.darken_rgba(hnd[0].get_color(), 0.6)
            txt_alpha = 0.75 if is_extrapolated else 1.0
            bbox = dict(facecolor="white", ec="none", alpha=bbox_alpha * txt_alpha, pad=1)
            ax.text(
                txy[0], txy[1], overhead_str,
                transform=ax.transAxes,
                ha="center", va="bottom",
                fontsize=annotsz, color=txtcolor, bbox=bbox, alpha=txt_alpha,
            )

    ax.set_xlabel(r"\textbf{Ranks}")
    ax.set_ylabel(r"\textbf{Relative Runtime}")

    ax.set_xscale("log")
    ax.set_xticks(all_nranks)
    ax.set_xticklabels([f"{x}" for x in all_nranks])
    ax.xaxis.set_minor_formatter(mtick.NullFormatter())
    ax.xaxis.set_minor_locator(mtick.NullLocator())

    ax.set_ylim(1, 2)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x*100:.0f}\%"))
    ax.yaxis.set_major_locator(mtick.MultipleLocator(0.2))
    ax.yaxis.set_minor_locator(mtick.MultipleLocator(0.05))

    ax.grid(which="major", color="#bbb")
    ax.yaxis.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)


def plot_runtime_line():
    rdf = prep_and_extrapolate()
    c.set_colormap("Pastel1-Dark")

    fig, ax = plt.subplots(1, 1, figsize=(4, 4))
    plot_runtime_line_inner(ax, rdf)

    fig.tight_layout(pad=0.3)

    c.save_plot(fig, "tracer_runtimes_line", subdir="sb")

    sb_runtime_line(fig, ax)

    plt.close("all")


def sb_runtime_line(fig, ax):
    # Debug: print artist indices
    # for i, artist in enumerate(ax.get_children()):
    #     print(f"{i}: {type(artist).__name__}")

    sb = c.StagedBuildout(ax, fig, "tracer_runtimes_line")
    # Each frame: [line, annotation_text]
    sb.add_frame([1, 2], [], [])   # ORCA
    sb.add_frame([3, 4, 5, 6], [], [])   # TAU and dftracer
    sb.add_frame([7, 8, 9, 10], [], [])   # Score-P and caliper
    sb.build()
    #
    pass

if __name__ == "__main__":
    plt.style.use(c.get_plotsrc_dir() / "ppt.mplstyle")
    plot_runtime_line()
