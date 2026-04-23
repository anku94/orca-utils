# Section 6: Related Work

## Categories

**In-Situ Systems**
- DeltaFS, ADIOS, ALPINE
- CARP: shuffling-based partitioning precedent

**Monitoring & Metrics**
- LDMS (Sandia), InfiniBand network monitoring

**Tracing Systems**
- HPC: Score-P, TAU, OTF2
- Distributed: Fay, Snicket, Magpie
- BSP-aware: DFTracer (Dask cluster), TAU+MRNet

**ML Observability**
- PyTorch Kineto, HTA, DFTracer
- TrainCheck, XPUTimer, Minder, Aegis, Holmes, GREYHOUND
- MegaScale: NCCL bootstrap optimization example

**Analytics Frameworks**
- Hatchet (callgraph index on pandas)
- Pipit (pandas on OTF2)
- SciQL, MeshSQL, TileDB

**Hardware & Accelerators**
- Arrow for particle data + SmartNICs
- eGPU: extending eBPF to GPUs

**Analogy**
- SLAC/LHC: FPGA-based DAQ filters 99% at source
- ORCA = software-defined equivalent
