import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import common as c
from trace_sizes import prep_tracesz_dataset, fmtbytes, get_range_str, ONE_GB


def plot_tracesz_left(ax: plt.Axes, szdf, profiles):
    annotsz = plt.rcParams["font.size"] - 3

    for pidx, profile in enumerate(profiles):
        szdf_profile = szdf[szdf["profile"] == profile]
        data_x = szdf_profile["ranks"]
        data_y = szdf_profile["trace_size"]
        pprops = c.PROF_PROPS[c.Prof(profile)]
        hnd = ax.plot(data_x, data_y, marker=pprops.marker, label=pprops.label, color=pprops.color, mec="black", alpha=0.7)

        # annotate points
        mult_str = get_range_str(szdf_profile["tracesz_mult"])
        all_txy = [
            (0.50, 0.43),
            (0.52, 0.58),
            (0.55, 0.70),
            (0.57, 0.84),
            (0.7, 0.97),
        ]
        txy = all_txy[pidx]

        if txy is not None:
            txtcolor = c.darken_rgba(hnd[0].get_color(), 0.6)
            bbox = dict(facecolor="white", ec="none", alpha=0.4, pad=1)
            rot = 15
            ax.text(txy[0], txy[1], mult_str, transform=ax.transAxes, ha="center", va="top", fontsize=annotsz, color=txtcolor, bbox=bbox, rotation=rot)

    ax.set_xlabel(r"\textbf{Ranks}")
    ax.set_ylabel(r"\textbf{Trace Size}")
    ax.set_yscale("log")
    ax.set_ylim(bottom=ONE_GB)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: fmtbytes(x)))
    ax.yaxis.set_minor_formatter(mtick.NullFormatter())
    ax.yaxis.set_major_locator(mtick.LogLocator(base=4, numticks=50))
    ax.yaxis.set_minor_locator(mtick.LogLocator(base=4, subs=[2, 3], numticks=50))

    all_nranks = [512, 1024, 2048, 4096]
    ax.set_xscale("log")
    ax.set_xticks(all_nranks)
    ax.set_xticklabels([f"{x}" for x in all_nranks])
    ax.xaxis.set_minor_formatter(mtick.NullFormatter())
    ax.xaxis.set_minor_locator(mtick.NullLocator())

    ax.grid(which="major", color="#bbb")
    ax.yaxis.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)


def plot_trace_sizes():
    szdf = prep_tracesz_dataset()
    profiles = szdf["profile"].unique().tolist()
    c.set_colormap("Pastel1-Dark")

    fig, ax = plt.subplots(1, 1, figsize=(4.0, 4.0))
    plot_tracesz_left(ax, szdf, profiles)

    fig.tight_layout(pad=0.3)
    c.save_plot(fig, "trace_sizes", subdir="sb")

    sb_trace_sizes(fig, ax)

    plt.close("all")


def sb_trace_sizes(fig, ax):
    # Debug: print artist indices
    # for i, a in enumerate(ax.get_children()):
    #     print(i, type(a).__name__, getattr(a, 'get_label', lambda: '')())

    # Indices: ORCA(0), TAU(1,2), Score-P(3,4), DFTracer(5,6), Caliper(7,8)
    # Build order (same as runtimes): TAU+DFTracer → Score-P+Caliper → ORCA

    sb = c.StagedBuildout(ax, fig, "trace_sizes")
    # Frame 3: ORCA
    sb.add_frame([0, 1], [], [])
    # Frame 2: Score-P + Caliper
    #sb.add_frame([3, 4, 7, 8], [], [])
    sb.add_frame([4, 5, 8, 9], [], [])
    # Frame 1: TAU + DFTracer
    #sb.add_frame([1, 2, 5, 6], [], [])
    sb.add_frame([2, 3, 6, 7], [], [])
    sb.build()


if __name__ == "__main__":
    plt.style.use(c.get_plotsrc_dir() / "ppt.mplstyle")
    plot_trace_sizes()
