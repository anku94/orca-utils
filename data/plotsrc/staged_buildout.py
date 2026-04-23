import glob as glob
import matplotlib.figure as pltfig
import matplotlib.pyplot as plt
import re

from typing import Union


def plot_init():
    SMALL_SIZE = 12
    MEDIUM_SIZE = 14
    BIGGER_SIZE = 26

    plt.rc("font", size=SMALL_SIZE)  # controls default text sizes
    plt.rc("axes", titlesize=SMALL_SIZE)  # fontsize of the axes title
    plt.rc("axes", labelsize=MEDIUM_SIZE)  # fontsize of the x and y labels
    plt.rc("xtick", labelsize=SMALL_SIZE)  # fontsize of the tick labels
    plt.rc("ytick", labelsize=SMALL_SIZE)  # fontsize of the tick labels
    plt.rc("legend", fontsize=SMALL_SIZE)  # legend fontsize
    plt.rc("figure", titlesize=BIGGER_SIZE)  # fontsize of the figure title


def plot_init_big():
    SMALL_SIZE = 15
    MEDIUM_SIZE = 16
    BIGGER_SIZE = 22

    plt.rc("font", size=SMALL_SIZE)  # controls default text sizes
    plt.rc("axes", titlesize=BIGGER_SIZE)  # fontsize of the axes title
    plt.rc("axes", labelsize=MEDIUM_SIZE)  # fontsize of the x and y labels
    plt.rc("xtick", labelsize=SMALL_SIZE)  # fontsize of the tick labels
    plt.rc("ytick", labelsize=SMALL_SIZE)  # fontsize of the tick labels
    plt.rc("legend", fontsize=SMALL_SIZE)  # legend fontsize
    plt.rc("legend", fontsize=14)  # legend fontsize
    plt.rc("figure", titlesize=BIGGER_SIZE)  # fontsize of the figure title


def plot_init_print():
    SMALL_SIZE = 16
    MEDIUM_SIZE = 18
    BIGGER_SIZE = 20

    plt.rc(
        "font", size=SMALL_SIZE
    )  # controls default text sizes plt.rc("axes", titlesize=SMALL_SIZE)  # fontsize of the axes title
    plt.rc("axes", labelsize=MEDIUM_SIZE)  # fontsize of the x and y label
    plt.rc("xtick", labelsize=SMALL_SIZE)  # fontsize of the tick labels
    plt.rc("ytick", labelsize=SMALL_SIZE)  # fontsize of the tick labels
    plt.rc("legend", fontsize=SMALL_SIZE)  # legend fontsize
    plt.rc("figure", titlesize=BIGGER_SIZE)  # fontsize of the figure title


def plot_dir_latest() -> str:
    dir_latest = "../plots"
    return dir_latest


class PlotSaver:
    @staticmethod
    def save(
        fig: pltfig.Figure,
        trpath: Union[str, None],
        fpath: Union[str, None],
        fname: str,
    ):
        PlotSaver._save_to_fpath(fig, trpath, fpath, fname, ext="pdf", show=False)

    @staticmethod
    def _save_to_fpath(
        fig: pltfig.Figure,
        trpath: Union[str, None],
        fpath: Union[str, None],
        fname: str,
        ext="png",
        show=True,
    ):
        trpref = ""
        if trpath is not None:
            if "/" in trpath:
                trpref = trpath.split("/")[-1] + "_"
            elif len(trpath) > 0:
                trpref = f"{trpath}_"

        if fpath is None:
            fpath = plot_dir_latest()

        full_path = f"{fpath}/{trpref}{fname}.{ext}"

        if show:
            print(f"[PlotSaver] Displaying figure\n")
            fig.show()
        else:
            print(f"[PlotSaver] Writing to {full_path}\n")
            fig.savefig(full_path, dpi=300)


class StagedBuildout:
    def __init__(self, ax: plt.Axes):
        self.ax = ax

        handles, labels = ax.get_legend_handles_labels()
        self.ohandles = handles
        self.olabels = labels
        self.olegvis = [True] * len(handles)

        self.oxlabels = ax.get_xticklabels()
        self.oxvis = [True] * len(self.oxlabels)

    def disable_legend_entry(self, index: int):
        self.olegvis[index] = False
        self.rebuild_legend()

    def enable_legend_entry(self, index: int):
        self.olegvis[index] = True
        self.rebuild_legend()

    def toggle_legend_entry(self, index: int):
        self.olegvis[index] = not self.olegvis[index]
        self.rebuild_legend()

    def disable_xticklabel(self, index: int):
        self.oxlabels[index].set_visible(False)
        self.oxvis[index] = False

    def enable_xticklabel(self, index: int):
        self.oxlabels[index].set_visible(True)
        self.oxvis[index] = True

    def rebuild_legend(self):
        handles = [h for h, v in zip(self.ohandles, self.olegvis) if v]
        labels = [l for l, v in zip(self.olabels, self.olegvis) if v]
        self.draw_legend(handles, labels)
        # self.ax.legend(handles, labels, ncol=1, markerscale=0.5, loc="lower left")

    def disable_artists(self, indices: list[int]):
        artists = self.ax.get_children()
        for i in indices:
            artists[i].set_visible(False)

    def enable_artists(self, indices: list[int]):
        artists = self.ax.get_children()
        for i in indices:
            artists[i].set_visible(True)

    def toggle_artists(self, indices: list[int]):
        artists = self.ax.get_children()
        for i in indices:
            artists[i].set_visible(not artists[i].get_visible())

    def disable_alx(
        self, artists: list[int], legend_items: list[int] = [], x_items: list[int] = []
    ):
        self.disable_artists(artists)

        for item in legend_items:
            print(f"Disabling legend entry {item}")
            self.disable_legend_entry(item)

        for item in x_items:
            print(f"Disabling xticklabel {item}")
            self.disable_xticklabel(item)

    def enable_alx(
        self, artists: list[int], legend_items: list[int] = [], x_items: list[int] = []
    ):
        self.enable_artists(artists)
        for item in legend_items:
            self.enable_legend_entry(item)

        for item in x_items:
            self.enable_xticklabel(item)

    def draw_legend(self, handles, labels):
        self.ax.legend(handles, labels)
