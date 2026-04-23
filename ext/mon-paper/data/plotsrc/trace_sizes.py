import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import common as c

ONE_GB = 2**30


def fmtbytes(x: float) -> str:
    labels = ["B", "KB", "MB", "GB", "TB"]
    lidx = 0
    while x >= 1024 and lidx < len(labels) - 1:
        x /= 1024
        lidx += 1

    xstr: str = ""
    if x < 10:
        xstr = f"{x:.2f}"
    elif x < 100:
        xstr = f"{x:.1f}"
    else:
        xstr = f"{x:.0f}"

    return f"{xstr}\,{labels[lidx]}"


def prep_scaled_szdf():
    szdf0_path = c.get_plotdata_dir() / "tracesizes" / "20251229.csv"
    szdf0 = pd.read_csv(szdf0_path)
    profs0 = [c.Prof.ORCA_TGT, c.Prof.TAU_TGT, c.Prof.DFTRACER_TGT]
    szdf0 = szdf0[szdf0["profile"].isin(profs0)]

    szdf1_path = c.get_plotdata_dir() / "tracesizes" / "20260106.csv"
    szdf1 = pd.read_csv(szdf1_path)
    profs1 = [c.Prof.SCOREP_TGT, c.Prof.CALIPER_TGT]

    szdf1 = szdf1[szdf1["profile"].isin(profs1)]
    szdf1_n200 = szdf1[szdf1["steps"] == 200].copy()
    szdf1_n20 = szdf1[szdf1["steps"] == 20].copy()

    # construct 2k by multiplying 200 data by 10
    szdf1_n2k = szdf1_n200.copy()
    szdf1_n2k["trace_size"] = szdf1_n2k["trace_size"] * 10
    szdf1_n2k["steps"] = 2000

    szdf1_scaled = pd.concat([szdf1_n20, szdf1_n2k], ignore_index=True)
    szdf = pd.concat([szdf0, szdf1_scaled], ignore_index=True)

    # all_profiles = profs0 + profs1
    all_profiles = [
        c.Prof.ORCA_TGT,
        c.Prof.TAU_TGT,
        c.Prof.SCOREP_TGT,
        c.Prof.DFTRACER_TGT,
        c.Prof.CALIPER_TGT,
    ]
    szdf["profile"] = pd.Categorical(
        szdf["profile"], categories=all_profiles, ordered=True
    )

    return szdf


def prep_tracesz_dataset():
    szdf = prep_scaled_szdf()
    szdf.sort_values(by=["profile", "ranks", "steps"], inplace=True)
    szdf20 = szdf[(szdf["steps"] == 20) & (szdf["evtcnt"] != -1)]
    szdf20 = (
        szdf20.groupby(["ranks", "profile"])
        .agg({"trace_size": "mean", "evtcnt": "mean"})
        .reset_index()
    )
    szdf20["perevtsz"] = szdf20["trace_size"] / szdf20["evtcnt"]
    baseevtsz = (
        szdf20[szdf20["profile"] == "07_or_tracetgt"]
        .loc[:, ["ranks", "perevtsz"]]
        .rename(columns={"perevtsz": "base_perevtsz"})
    )
    szdf20 = szdf20.merge(baseevtsz, on="ranks", how="left")
    szdf20["perevtsz_mult"] = szdf20["perevtsz"] / szdf20["base_perevtsz"]

    # drop column trace_size
    szdf20.drop(columns=["trace_size"], inplace=True)

    szdf2k = szdf[szdf["steps"] == 2000]
    szdf2k = (
        szdf2k.groupby(["ranks", "profile"]).agg({"trace_size": "mean"}).reset_index()
    )

    basesz = (
        szdf2k[szdf2k["profile"] == "07_or_tracetgt"]
        .loc[:, ["ranks", "trace_size"]]
        .rename(columns={"trace_size": "base_tracesz"})
    )
    szdf2k = szdf2k.merge(basesz, on="ranks", how="left")
    szdf2k["tracesz_mult"] = szdf2k["trace_size"] / szdf2k["base_tracesz"]

    szdf_final = szdf2k.merge(szdf20, on=["ranks", "profile"], how="left")

    return szdf_final


def get_range_str(vals: pd.Series) -> str:
    return f"\\sffamily\\bfseries {vals.min():.1f}$\\times$--{vals.max():.1f}$\\times$"


def plot_tracesz_line_left(ax: plt.Axes, szdf: pd.DataFrame, profiles: list[str]):
    annotsz = plt.rcParams["font.size"] - 3

    for pidx, profile in enumerate(profiles):
        szdf_profile = szdf[szdf["profile"] == profile]
        data_x = szdf_profile["ranks"]
        data_y = szdf_profile["trace_size"]
        pprops = c.PROF_PROPS[c.Prof(profile)]
        hnd = ax.plot(data_x, data_y, marker=pprops.marker, label=pprops.label, color=pprops.color, mec="black", alpha=0.7) # fmt: skip

        # annotate points
        mult_str = get_range_str(szdf_profile["tracesz_mult"])
        all_txy = [
            None,
            (0.52, 0.58),
            (0.55, 0.72),
            (0.55, 0.85),
            (0.6, 0.98),
        ]
        txy = all_txy[pidx]

        if txy is not None:
            txtcolor = c.darken_rgba(hnd[0].get_color(), 0.6)
            bbox = dict(facecolor="white", ec="none", alpha=0.4, pad=1)
            rot = 10
            ax.text(txy[0], txy[1], mult_str, transform=ax.transAxes, ha="center", va="top", fontsize=annotsz, color=txtcolor, bbox=bbox, rotation=rot)  # fmt: skip

    ax.set_xlabel(r"\textbf{MPI Ranks}")
    ax.set_ylabel(r"\textbf{Trace Size}")
    ax.set_yscale("log")
    # ax.yaxis.set_major_locator(mtick.MultipleLocator(256 * ONE_GB))
    ax.set_ylim(bottom=ONE_GB)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: fmtbytes(x)))
    ax.yaxis.set_minor_formatter(mtick.NullFormatter())
    ax.yaxis.set_major_locator(mtick.LogLocator(base=4, numticks=50))
    ax.yaxis.set_minor_locator(mtick.LogLocator(base=4, subs=[2, 3], numticks=50))


def plot_tracesz_line_right(ax: plt.Axes, szdf: pd.DataFrame, profiles: list[str]):
    annotsz = plt.rcParams["font.size"] - 3

    for pidx, profile in enumerate(profiles):
        szdf_profile = szdf[szdf["profile"] == profile]
        data_x = szdf_profile["ranks"]
        data_y = szdf_profile["perevtsz"]
        pprops = c.PROF_PROPS[c.Prof(profile)]

        hnd = ax.plot(data_x, data_y, marker=pprops.marker, color=pprops.color, mec="black", alpha=0.7) # fmt: skip
        txtcolor = c.darken_rgba(hnd[0].get_color(), 0.6)
        mult_str = get_range_str(szdf_profile["perevtsz_mult"])

        all_txy = [None, (0.25, 0.56), (0.75, 0.56), (0.5, 0.95), (0.5, 0.70)]
        txy = all_txy[pidx]

        if txy is not None:
            bbox = dict(facecolor="white", ec="none", alpha=0.4, pad=1)
            ax.text(txy[0], txy[1], mult_str, transform=ax.transAxes, ha="center", va="top", fontsize=annotsz, color=txtcolor, bbox=bbox) # fmt: skip

    ax.set_yscale("log")
    ax.set_ylim(1, 256)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:.0f}\,B"))
    ax.yaxis.set_minor_formatter(mtick.NullFormatter())
    ax.yaxis.set_major_locator(mtick.LogLocator(base=2, numticks=50))
    ax.yaxis.set_minor_locator(mtick.LogLocator(base=2, subs=[1.5], numticks=50))
    ax.set_ylabel(r"\textbf{Record Size (B)}")
    ax.set_xlabel(r"\textbf{MPI Ranks}")


def plot_tracesz_line():
    # plot all tracesizes as a single line plot
    szdf = prep_tracesz_dataset()
    profiles = szdf["profile"].unique().tolist()
    print(profiles)
    c.set_colormap("Pastel1-Dark")
    print(szdf)

    all_nranks = [512, 1024, 2048, 4096]
    # plt.close("all")

    fig, axes = plt.subplots(1, 2, figsize=(c.TEXTWIDTH * 0.5, 1.6))
    [ax.clear() for ax in axes]

    plot_tracesz_line_left(axes[0], szdf, profiles)
    plot_tracesz_line_right(axes[1], szdf, profiles)

    for ax in axes:
        ax.set_xscale("log")
        ax.set_xticks(all_nranks)
        ax.set_xticklabels([f"{x}" for x in all_nranks])
        # ax.xaxis.set_major_formatter(mtick.ScalarFormatter())
        ax.xaxis.set_minor_formatter(mtick.NullFormatter())
        ax.xaxis.set_minor_locator(mtick.NullLocator())
        ax.grid(which="major", color="#bbb")
        ax.yaxis.grid(which="minor", color="#ddd")
        ax.set_axisbelow(True)

    axes[0].set_xlabel(r"\textbf{Ranks}", ha="right")
    axes[0].xaxis.set_label_coords(-0.1, -0.07)
    axes[1].set_xlabel("")

    lfsz = plt.rcParams["legend.fontsize"] - 1
    lbbox = (0.51, 1.01)
    legh, legl = axes[0].get_legend_handles_labels()
    print(legh, legl)
    ltoflag = ["Score-P", "Caliper"]
    legl = [f"{l}*" if l in ltoflag else l for l in legl]

    lobj = fig.legend(legh, legl, loc="outside upper center", ncols=len(profiles), bbox_to_anchor=lbbox, fontsize=lfsz) # fmt: skip
    for l in lobj.get_texts():
        if l.get_text().endswith("*"):
            l.set_color(c.SpecialColors.FLAG.value)

    fig.tight_layout(pad=0.2)
    fig.subplots_adjust(top=0.83, bottom=0.12)
    c.save_plot(fig, "amr_tracesizes_line")
    plt.close("all")


if __name__ == "__main__":
    plt.style.use(c.get_plotsrc_dir() / "paper.mplstyle")
    c.set_colormap("Pastel1")
    plot_tracesz_line()
