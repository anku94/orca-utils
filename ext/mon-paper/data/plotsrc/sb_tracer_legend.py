import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import common as c

# Profiles in order: Baseline to Caliper
PROFILES = [
    #c.Prof.BASELINE,
    c.Prof.ORCA_TGT,
    c.Prof.TAU_TGT,
    c.Prof.DFTRACER_TGT,
    c.Prof.SCOREP_TGT,
    c.Prof.CALIPER_TGT,
]


def plot_legend_only():
    fig, ax = plt.subplots(1, 1, figsize=(9, 0.6))
    ax.axis("off")

    flagged = [c.Prof.SCOREP_TGT, c.Prof.CALIPER_TGT]

    handles = []
    labels = []
    for prof in PROFILES:
        props = c.PROF_PROPS[prof]
        h = mlines.Line2D(
            [], [],
            marker=props.marker,
            color=props.color,
            mec="black",
            linestyle="-",
            label=props.label,
        )
        handles.append(h)
        lbl = f"{props.label}*" if prof in flagged else props.label
        labels.append(lbl)

    leg = fig.legend(
        handles, labels,
        loc="center",
        ncol=len(PROFILES),
        fontsize=plt.rcParams["legend.fontsize"],
        columnspacing=1.0,
        handletextpad=0.4,
    )
    for txt in leg.get_texts():
        if txt.get_text().endswith("*"):
            txt.set_color(c.SpecialColors.FLAG.value)

    fig.tight_layout(pad=0.1)
    c.save_plot(fig, "tracer_legend", subdir="sb")
    plt.close("all")


if __name__ == "__main__":
    plt.style.use(c.get_plotsrc_dir() / "ppt.mplstyle")
    c.set_colormap("Pastel1-Dark")
    plot_legend_only()
