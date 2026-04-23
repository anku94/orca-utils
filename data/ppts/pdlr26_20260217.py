from pathlib import Path
from pptapi import (
    ContentSlide,
    EvalSlide,
    MarkdownList,
    Text,
    Slide,
    build_deck,
    TitleSlide,
)

DATA_DIR = Path(__file__).parent / "data"
TEMPLATE = DATA_DIR / "pdltemplate.pptx"
SB_DIR = Path("/Users/schwifty/Repos/mon-paper/data/figs/sb")

slides: list[Slide] = []

# --- Title ---
s = TitleSlide(
    title="ORCA: Real-time Observability and Control\nfor Bulk-Synchronous Parallel Applications",
    subtitle="Ankush Jain",
)
slides.append(s)

# --- Pre-Background ---
# Overview slide: what this talk is about
s = ContentSlide(
    title="Overview",
    content=Text(""),
)
slides.append(s)

# --- Background ---

# Explain BSP
s = ContentSlide(
    title="Bulk-Synchronous Parallel (BSP) Applications",
    content=Text(""),
)

# SoTA is traces. Traces are the write-optimized ceiling — can't ingest faster
# than a local append. Kafka/ClickHouse is the same model with a network hop.
# Bullets: overcollection, delayed feedback, no workload semantics, no fabric awareness.
# Visual: broken-loop diagram showing the write-then-read cycle.
s = ContentSlide(
    title="Traces Create Visibility Bottlenecks",
    content=Text(""),
)
slides.append(s)

# Reframe from tools to what you actually want: view + action = loop.
# Defining as a loop: views collect minimum necessary, online means fast
# refinement + intervention. This is steerable observability.
# Bullets: meaningful views, targeted action, minimum data, online refinement.
# Visual: clean loop diagram + spectrum figure.
s = ContentSlide(
    title="Observability As A Feedback Loop",
    content=Text(""),
)
slides.append(s)

# BSP sync creates causal boundaries (defines views as timestep dataframes)
# and consistent intervention windows (defines action as timestep-aligned control).
# Microservices got this with Dapper/spans. BSP never did.
# Bullets: causal partitioning → views, sync windows → intervention,
#          no existing language, Dapper did this for microservices.
# Visual: bsp.pdf with timestep dataframe bracket + observation/intervention callouts.
s = ContentSlide(
    title="BSP Structure Defines The Loop",
    content=Text(""),
)
slides.append(s)

# Requirements that emerge from the feedback loop framing + BSP structure.
# Each maps to an ORCA component (don't say it yet).
# BSP-Aware Semantic Guarantees → TBON + timestep dataframes
# Low-Cost, Low-Latency Feedback → RDMA transport + pushdown
# Declarative and Flexible Analytics → OrcaFlow
s = ContentSlide(
        title="Steerable Observability: Requirements",
    content=Text(""),
)
slides.append(s)

# --- Evaluation ---
s = EvalSlide(
    title="Runtime Overhead",
    bullets=MarkdownList(
        """
- Compare with TAU, DFTracer, Score-P, Caliper
- Measure relative runtime
- 512 to 4096 ranks
"""
    ),
    figures=sorted(SB_DIR.glob("tracer_runtimes_line_*.pdf")),
)
slides.append(s)


def main():
    ppt_fpath = DATA_DIR / "pdlr26.pptx"
    build_deck(slides, ppt_fpath, TEMPLATE)


if __name__ == "__main__":
    main()
