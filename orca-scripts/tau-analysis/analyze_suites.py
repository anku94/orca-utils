from suite_utils import *

def run():
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_fpath = os.path.join(parent_dir, "suites.yaml")
    all_suites = read_suites(yaml_fpath)
    print(all_suites)

    s512 = ["r512_a1_n20_v2", "r512_a1_n200_v2", "r512_a1_n2000_v2"]

if __name__ == "__main__":
    run()