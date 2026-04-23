import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import common as c
from tracer_runtimes import fill_baseline, prep_runtime_data, set_bar_hatch, fmt_overhead

ONE_GB = 2**30
PROFILES = [c.Prof.ORCA_TGT, c.Prof.DFTRACER_TGT, c.Prof.DFTRACER_COMP]


def prep_runtime() -> pd.DataFrame:
    base_path = c.get_plotdata_dir() / "runtimes" / "20251229.csv"
    dft_path = c.get_plotdata_dir() / "runtimes" / "20260121.csv"

    base_df = pd.read_csv(base_path)
    dftc_df = pd.read_csv(dft_path)
    df = pd.concat([base_df, dftc_df], ignore_index=True)
    df = fill_baseline(df, "00_noorca")

    rdf = prep_runtime_data(df, PROFILES)
    rdf = rdf[rdf["ranks"] == 512]
    return rdf


def prep_tracesize() -> pd.DataFrame:
    base_path = c.get_plotdata_dir() / "tracesizes" / "20251229.csv"
    dft_path = c.get_plotdata_dir() / "tracesizes" / "20260121.csv"

    base_df = pd.read_csv(base_path)
    dftc_df = pd.read_csv(dft_path)
    df = pd.concat([base_df, dftc_df], ignore_index=True)

    df = df[df["profile"].isin(PROFILES)]
    df = df[(df["ranks"] == 512) & (df["steps"] == 2000)]
    df["profile"] = pd.Categorical(df["profile"], categories=PROFILES, ordered=True)

    szdf = df.groupby("profile").agg({"trace_size": ["mean", "std"]}).reset_index()
    szdf.columns = ["profile", "size_mean", "size_std"]
    return szdf


def plot_dftc_runtime(ax: plt.Axes, rdf: pd.DataFrame):
    xlabels = [c.PROF_PROPS[p].label for p in PROFILES]

    data_x = np.arange(len(rdf))
    data_y = rdf["tsecs_base_mean"]
    data_yxtra = rdf["tsecs_mean"] - data_y
    data_yerr = rdf["tsecs_std"]

    base_bars = ax.bar(data_x, data_y, ec="black", fc="C3")
    xtra_bars = ax.bar(data_x, data_yxtra, bottom=data_y, yerr=data_yerr, ec="black", fc="C0", capsize=4)
    set_bar_hatch(base_bars, "\\\\\\")
    set_bar_hatch(xtra_bars, "xxx")

    xtra_pcts = (data_yxtra / data_y) * 100
    xtra_labels = [fmt_overhead(x) for x in xtra_pcts]
    fontsz = plt.rcParams["font.size"]
    bbox = dict(facecolor="white", edgecolor="none", alpha=0.6, pad=1)
    ax.bar_label(xtra_bars, labels=xtra_labels, label_type="edge", fontsize=fontsz - 2, rotation=90, padding=2, bbox=bbox)

    ax.set_xticks(data_x)
    ax.set_xticklabels(xlabels, rotation=25, ha="right", rotation_mode="anchor")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:.0f}\,s"))
    ax.yaxis.set_major_locator(mtick.MultipleLocator(500))
    ax.yaxis.set_minor_locator(mtick.MultipleLocator(100))
    ax.text(-0.05, 1.02, r"\textbf{Runtime}", transform=ax.transAxes, ha="left", va="bottom")
    ax.tick_params(axis="y", pad=1)
    ax.tick_params(axis="x", pad=1)
    ax.set_ylim(0, 2600)


def plot_dftc_tracesize(ax: plt.Axes, szdf: pd.DataFrame):
    xlabels = [c.PROF_PROPS[p].label for p in PROFILES]

    data_x = np.arange(len(szdf))
    data_y = szdf["size_mean"] / ONE_GB
    data_yerr = szdf["size_std"] / ONE_GB

    bars = ax.bar(data_x, data_y, yerr=data_yerr, ec="black", fc="C3", capsize=4)
    set_bar_hatch(bars, "\\\\\\")

    # Multiplier labels relative to ORCA (first bar)
    base_size = szdf["size_mean"].iloc[0]
    mults = szdf["size_mean"] / base_size
    # mult_labels = [f"{m:.0f}$\\times$" if m > 1.5 else "1$\\times$" for m in mults]
    mult_labels = [f"\\textbf{{{m:.1f}}}$\\mathbf{{\\times}}$" for m in mults]
    fontsz = plt.rcParams["font.size"]
    bbox = dict(facecolor="white", edgecolor="none", alpha=0.6, pad=1)
    ax.bar_label(bars, labels=mult_labels, label_type="edge", fontsize=fontsz - 2, padding=2, bbox=bbox)

    ax.set_xticks(data_x)
    ax.set_xticklabels(xlabels, rotation=25, ha="right", rotation_mode="anchor")
    ax.set_ylim((0, 300))
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:.0f}\,GB"))
    ax.yaxis.set_major_locator(mtick.MultipleLocator(50))
    ax.yaxis.set_minor_locator(mtick.MultipleLocator(10))
    ax.grid(which="major", color="#bbb")
    ax.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)
    ax.text(-0.05, 1.02, r"\textbf{Trace Size}", transform=ax.transAxes, ha="left", va="bottom")
    ax.tick_params(axis="y", pad=1)
    ax.tick_params(axis="x", pad=1)


def plot_dftracer_comp():
    rdf = prep_runtime()
    szdf = prep_tracesize()

    fig, axes = plt.subplots(1, 2, figsize=(c.COLWIDTH * 0.66, 1.4))

    plot_dftc_runtime(axes[0], rdf)
    plot_dftc_tracesize(axes[1], szdf)

    for ax in axes:
        ax.grid(which="major", color="#bbb")
        ax.yaxis.grid(which="minor", color="#ddd")
        ax.set_axisbelow(True)

    fig.tight_layout(pad=0.3)
    fig.subplots_adjust(bottom=0.27)
    c.save_plot(fig, "dftracer_comp")
    plt.close("all")


def run():
    plot_dftracer_comp()


if __name__ == "__main__":
    plt.style.use(c.get_plotsrc_dir() / "paper.mplstyle")
    c.set_colormap("Pastel1")
    run()
