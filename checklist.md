# SC Submission Checklist

Authors must complete this checklist to ensure their submission meets the expectations for clarity, rigor, and reproducibility in HPC research. The checklist is designed to guide preparation and review of the manuscript.

For each item:

- Indicate **Yes**, **No**, or **N/A** (Not Applicable) in the corresponding question.
- If No or N/A, briefly explain the reason (e.g., "not applicable to analytical studies," "artifact under embargo," "baseline unavailable for architecture").
- Responses should be specific, concise, and factual.
- Include references to the relevant sections, figures, or tables in your paper (e.g., "Section 4.2," "Table 3").
- All questions should be addressed explicitly, even if the answer is negative.

### Examples

> **Have you provided quantitative evidence or benchmarks to motivate the specific problem?**
>
> Yes. The objective is defined in Section 1.1. It emphasizes performance optimization for exascale climate simulations.

> **Have you identified and summarized the most relevant and recent prior work?**
>
> Yes. Section 2 reviews six state-of-the-art distributed memory solvers published between 2022–2025.

> **Have you discussed how conclusions might change under different problem scales, architectures, or workloads?**
>
> N/A. The work focuses exclusively on shared-memory systems. Heterogeneous and distributed architectures are out of scope.

---

## 1. Scope

**Primary Track: Data Analytics, Visualization & Storage**

Selected focus areas:
- I/O performance tuning and middleware
- In situ data processing and visualization
- Visual analytics for supercomputing systems, application monitoring, and machine learning model interpretation and tuning at scale

**Secondary Track: Performance Measurement, Modeling, and Tools**

Selected focus areas:
- Scalable tools and instrumentation infrastructure for measurement, monitoring, and/or visualization of performance

Briefly describe how your contribution fits within the scope of HPC and how it addresses the specific focus of the selected track(s):

>

ORCA enables real-time feedback loops over HPC workloads. It enables in-situ/post-hoc analyses using columnar dataframe-style APIs, along with online interventions (live steering/tuning) in response.  ORCA ingests telemetry from HPC applications, enables in-situ and post-hoc analyses using While motivated by telemetry analytics, it potentially extends to other scientific data analysis use cases (discussed in Sec. 7).

---

## 2. Motivation and Problem Definition

- [x] Have you clearly stated the research objective and its scientific or technical importance?
- [x] Have you defined the problem scope and assumptions with sufficient precision?
- [x] Have you provided quantitative evidence or benchmarks to motivate your problem?

**Explain:**

>

- Research objective stated in introduction (always-on, steerable observability)
- Scope/requirements defined in Sec. III.
- Motivation is primarily qualitative (slow workflows), evidence is provided as extensive case studies (citations 5-24), supplementary motivation benchmark in Sec. II-B.

---

## 3. Relation to State of the Art

- [x] Have you identified and summarized the most relevant and recent prior work?
- [x] Have you discussed how your work differs from and improves upon these prior efforts?
- [x] Have you articulated how your approach addresses gaps in the state of the art?
- [x] Have you verified the accuracy of all references and included DOIs where available?

**Explain:**

>

Gaps in prior work discussed in Sec. II-B, difference in II-C, DOIs included where available.

---

## 4. Contributions

- [x] Have you enumerated the main contributions, including theoretical, methodological, and empirical advances?
- [x] Have you demonstrated how these contributions advance or generalize existing knowledge in HPC?

**Explain:**

>

Contributions enumerated at the end of Sec. I as empirical results. Underlying methodological contributions (timestep dataframe abstraction, OrcaFlow distributed planner, TS2PC control protocol) are presented in Sec. IV. Generalizability beyond observability discussed in Sec. VII.

---

## 5. Experimental Methodology

- [x] Have you described the experimental or simulation environment, including hardware, software, and configuration details?
- [x] Have you validated correctness and discussed sources of measurement variability?
- [x] Have you provided quantitative results that include appropriate baselines and ablation studies where relevant?
- [x] Have you performed and reported statistical significance analysis for performance or accuracy improvements?
- [x] Have you examined potential barriers to reproducibility (e.g., hardware dependencies, software versions, or configuration settings) and discussed how they are addressed?

**Explain:**

>

- Hardware and software setup described in Sec. VI (cluster specs, fabric, MPI library, application). 
- Sources of variability discussed throughout (jitter from flush patterns, fabric contention, compression on critical path). 
- Baselines: four state-of-the-art tracers (Sec. VI-A). Ablations: compression impact and transport layer isolation in Sec. VI-A4, Fig. 8. 
- Error bars reported across all experiments (3 runs) where applicable. Variance is small relative to effect size and not visually prominent in figures.
- Reproducibility: ORCA is open source, application codes are public, software versions specified. Hardware is a specific research cluster with a legacy fabric, noted as a conservative evaluation environment (Sec. VI).


---

## 6. Limitations

- [x] Have you identified the main limitations or assumptions that constrain the proposed approach?
- [x] Have you discussed how conclusions might change under different problem scales, architectures, or workloads?

**Explain:**

>

- Assumptions noted throughout: BSP model with synchronization (Sec. III), cross-partition analytics limited to a single node (Sec. IV-C), control plane correctness and concurrency implications (Sec. V-B). 

- Hardware constraints acknowledged (legacy fabric, no QoS, CPU-only) and framed as lower bound on practically achievable benefits (Sec. VI). 

- Architectural implications evaluated in VII-A-4, discussed thoughout, relational model limitations and extensions discussed in VII.

---

## 7. Paper Format Requirements

- [x] Paper is limited to 10 two-column pages (U.S. letter – 8.5" x 11"), excluding bibliography
- [x] Uses IEEE Proceedings template (LaTeX or MS Word)
- [x] 10-page limit excludes AD/AE reproducibility appendices
- [x] DOIs included as `url` field (e.g., `https://doi.org/...`) or `note` field in BibTeX (not `doi` field, which IEEEtran.bst does not render)

---

## 8. [DONE] Double-Anonymous Review

- [x] No author names in heading or body
- [x] No affiliations in heading or body
- [x] No funding sources disclosed
- [x] No acknowledgments section
- [x] Complies with SC26 double-anonymous review policy

---

## 9. Usage of Large Language Models

Following IEEE and ACM policies, papers that include text generated from an LLM (e.g., ChatGPT) must disclose precisely how the tool was used and which part of the text was produced. See SC Policy on AI-Generated Text.

- [x] Was any text generated automatically for this work?

**If yes, describe how it was used:**

> Yes. Drafting and revision were assisted by Claude Opus 4.5 (Anthropic) and GPT-5 (OpenAI). All generated text was substantially edited and verified by the authors. No LLM-produced text appears verbatim.

---

## 10. Reproducibility Initiative

For SC26, an Artifact Description (AD) appendix is **mandatory** for all paper submissions by April 24. The Artifact Evaluation (AE) appendix remains optional but strongly encouraged.

AD/AE Appendices template: https://github.com/SC-Tech-Program/Author-Kit

- [x] I understand that I will have to complete an AD appendix after I submit my paper.

---

## 11. Gordon Bell Award

Papers submitted to the Gordon Bell Competition are not eligible for submission as regular SC papers. Authors must select either the Gordon Bell Competition or the Technical Papers track.

- [x] I confirm this submission is not simultaneously submitted to the Gordon Bell Competition.
