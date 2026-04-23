import random
import pandas as pd


def gen_evtimes(n: int, target: float, min_size: float = 1.0) -> list[float]:
    times = [random.uniform(min_size, target / n * 2) for _ in range(n)]
    scale = target / sum(times)
    return [t * scale for t in times]


def gen_trace(r: int, t: int, n: int, target_time: float) -> pd.DataFrame:
    data = []
    for rank in range(r):
        for ts in range(t):
            evtimes = gen_evtimes(n, target_time)
            evnames = [f"Event{chr(65 + i)}"
                       for i in range(n - 1)] + ["Barrier"]
            start = 0.0
            for evname, evtime in zip(evnames, evtimes):
                data.append({
                    "Rank": rank,
                    "Timestep": ts,
                    "Event": evname,
                    "Time": evtime,
                    "Start": start
                })
                start += evtime
    df = pd.DataFrame(data)
    df = df.astype({"Time": int, "Start": int})
    return df


def run():
    nranks = 4
    ntimesteps = 2
    nevents = 3
    target_time = 100.0

    df = gen_trace(nranks, ntimesteps, nevents, target_time)
    print(df.to_string(index=False))


if __name__ == "__main__":
    run()
