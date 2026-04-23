Very interesting paper. Implements a complete feedback loop. Uses Redis.

Money quotes:
- S4: "Synchronous training => all drop"
- S4: "Metrics do not detect stalls"

Greyhound: Detects BOCD (online changepoint detection) to differentiate fail-slows from outliers?

- BOCD models an underlying distribution to assess how/when distributions changed. Has false-positives

Locating stragglers:
- Uses lightweight profiling
- NCCL calls are injected to estimate execution times of each collective group
- Suspicious groups isolated

Validating:
- Pause simulation and run microbenchmarks


Ballparks (not in paper) by ChatGPT
- DP step duration: 10-60s
- TP step duration: 0.1-2ms

- DP parallelizes across batches, PP across microbatches
- PP microbatch to DP batch ratio: 8-128
- EP if used is within a PP stage, not all pipeline stages are EP
- whether TP is under EP or whether EP * TP is one dimension varies, as per ChatGPT
- As models scale, pressure towards TP being under EP

Adapting:
- S2: Adjust microbatch distribution
- S3: Adjust parallelism topology
- S4: Checkpoint and restart (prune nodes)

Eval notes:
- Sliding window is pretty darn good! It just misclassifies 2/392 events, vs their BOCD-V.