import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from models import get_profile_data

import pandas as pd


def exclude_invalid(data: pd.DataFrame) -> pd.DataFrame:
    not_invalid = (data['ovid'] != 'INVALID_AGG')
    return data[not_invalid]


def bytestostr(x, pos=None) -> str:
    units = ["B", "KB", "MB", "GB"]
    for unit in units:
        if x < 1024:
            return f"{x:.1f}{unit}"
        x /= 1024
    return f"{x:.1f}{unit}"


def counttostr(x, pos=None) -> str:
    units = ["", "K", "M", "B"]
    for unit in units:
        if x < 1000:
            return f"{x:.1f}{unit}"
        x /= 1000
    return f"{x:.1f}{units[-1]}"


def plot_cpu(ax, data):
    grouped = data.groupby(['ovid', 'metric_name'])

    for (ovid, metric_name), group in grouped:
        data_x = group['timestamp']
        data_y = group['metric_val']
        label = f"{ovid}-{metric_name}"
        ax.plot(data_x, data_y, label=label)

    ax.set_title("CPU %")
    ax.set_xlabel("Time")
    ax.set_ylabel("CPU Usage (%)")

    ax.grid(which="major", color="#bbb")
    ax.yaxis.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)
    ax.set_ylim(bottom=0, top=1)

    ax.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, pos: f"{x*100:.1f}%"))

    ax.legend()


def plot_msgsz(ax, data):
    grouped = data.groupby(['ovid', 'metric_name'])

    for (ovid, metric_name), group in grouped:
        data_x = group['timestamp']
        data_y = group['metric_val']
        label = f"{ovid}-{metric_name}"
        ax.plot(data_x, data_y, label=label)

    ax.set_title("RPC Message Size")
    ax.set_xlabel("Time")
    ax.set_ylabel("bytes")

    ax.grid(which="major", color="#bbb")
    ax.yaxis.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(bytestostr))
    ax.legend()


def plot_rate_bytes(ax, data):
    grouped = data.groupby(['ovid', 'metric_name'])

    for (ovid, metric_name), group in grouped:
        data_x = group['timestamp']
        data_y = group['metric_val']
        label = f"{ovid}-{metric_name}"
        ax.plot(data_x, data_y, label=label)

    ax.set_title("RPC Rate (Bytes)")
    ax.set_xlabel("Time")
    ax.set_ylabel("bytes/s")

    ax.grid(which="major", color="#bbb")
    ax.yaxis.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{bytestostr(x)}/s"))
    ax.legend()


def plot_rate_count(ax, data):
    grouped = data.groupby(['ovid', 'metric_name'])

    for (ovid, metric_name), group in grouped:
        data_x = group['timestamp']
        data_y = group['metric_val']
        label = f"{ovid}-{metric_name}"
        ax.plot(data_x, data_y, label=label)

    ax.set_title("RPC Rate (Count)")
    ax.set_xlabel("Time")
    ax.set_ylabel("msgs/s")

    ax.grid(which="major", color="#bbb")
    ax.yaxis.grid(which="minor", color="#ddd")
    ax.set_axisbelow(True)
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{counttostr(x)}/s"))
    ax.legend()


def run_plot():
    data = get_profile_data("rpc", "now-30m")

    fig, axes = plt.subplots(2, 2, figsize=(15, 10), sharex=True)
    ax0, ax1, ax2, ax3 = axes.flatten()

    for ax in axes.flatten():
        ax.clear()

    #plt.close('all')

    cpu_data = exclude_invalid(data["cpu_pct"])
    msgsz_data = exclude_invalid(data["msgsz"])
    rate_bytes_data = exclude_invalid(data["rate_bytes"])
    rate_count_data = exclude_invalid(data["rate_count"])

    plot_cpu(ax0, cpu_data)
    plot_msgsz(ax1, msgsz_data)
    plot_rate_bytes(ax2, rate_bytes_data)
    plot_rate_count(ax3, rate_count_data)

    fig.tight_layout()
    fig.show()

    plt.close('all')


def run():
    run_plot()


if __name__ == "__main__":
    run()
