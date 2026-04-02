import polars as pl
import glob

TRACE_ROOT = "/mnt/ltio/orcajobs"

class TraceData:
    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        self.trace_dirs = self.get_tracedirs(self.run_dir)

    @classmethod
    def get_tracedirs(cls, run_dir):
        trace_dirs = glob.glob(f"{run_dir}/pqroot/*")
        return trace_dirs

    @classmethod
    def get_tracefiles(cls, run_dir: str, trace_name: str):
        glob_patt = f"{run_dir}/pqroot/{trace_name}/**/*.parquet"
        trace_dirs = glob.glob(glob_patt, recursive=True)
        return trace_dirs

    def get_trace_files(self, trace_name: str):
        return self.get_tracefiles(self.run_dir, trace_name)

    def read_entire_trace(self, trace_name: str):
        trace_dir = f"{self.run_dir}/pqroot/{trace_name}"
        ds = pl.read_parquet(f"{trace_dir}/**/*.parquet", parallel="columns")

        return ds

def get_rundir(run_id: int) -> str:
    run_dir = f"{TRACE_ROOT}/run{run_id}"
    return run_dir


def get_last_rundir() -> str:
    ptr_path = "/mnt/ltio/orcajobs/current"
    dir_path = open(ptr_path, "r").read().strip()
    return dir_path
