import glob
import re
from typing import Union
import matplotlib.pyplot as plt
from datetime import datetime
import os


def get_plot_root() -> str:
    "Get the plot root as <pysrc>/figures"
    pysrc = os.path.dirname(os.path.abspath(__file__))
    plot_root = f"{pysrc}/figures"
    return plot_root


def get_suite_date(name: str) -> str:
    "Get a YYYYMMDD date from name, if not return TODAY"

    matches = re.findall(r"2025\d{4}", name)
    print(f"[get_suite_date] matches: {matches}")
    if len(matches) != 0:
        return matches[0]

    # return today's date
    return datetime.now().strftime("%Y%m%d")


def plot_dir_latest() -> str:

    all_dirs = glob.glob("figures/202*")

    def get_key(x: str) -> int:
        mobj = re.search(r"202[0-9]+", x)
        if mobj:
            return int(mobj.group(0))
        else:
            return -1

    dir_latest = max(all_dirs, key=get_key)
    return dir_latest


class PlotSaver:
    @staticmethod
    def save(fig: plt.Figure, fname: str, ext="png"):
        plot_root = get_plot_root()
        plot_date = get_suite_date(fname)
        plot_dir = f"{plot_root}/{plot_date}"

        # make dir if not exists
        if not os.path.exists(plot_dir):
            print(f"[PlotSaver] Creating directory: {plot_dir}")
            os.makedirs(plot_dir)

        plot_fpath = f"{plot_dir}/{fname}.{ext}"
        print(f"[PlotSaver] Writing to {plot_fpath}")
        fig.savefig(plot_fpath, dpi=300)