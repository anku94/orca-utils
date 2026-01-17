# AMR Performance Anomaly Analysis

**Study started:** ~2026-01-16 22:09 EST (upper bound, based on first artifact creation)
**Study completed:** 2026-01-16 22:34:43 EST

## Summary

The performance anomaly is caused by **blocking MPI operations hidden inside CommBuffer destructors** during mesh rebalancing. When `boundary_comm_map.clear()` is called, each `CommBuffer` destructor calls `MPI_Wait()` or `MPI_Cancel() + MPI_Wait()` to ensure pending communication completes. With ~200 buffers per rank, this creates serialized blocking waits totaling 70-84ms for affected ranks.

## The Real Root Cause

### CommBuffer Destructor (communication_buffer.cpp:45-74)

```cpp
template <class T>
CommBuffer<T>::~CommBuffer() {
#ifdef MPI_PARALLEL
  if (my_request_.use_count() == 1) {
    int flag;
    MPI_Status status;
    PARTHENON_MPI_CHECK(MPI_Test(my_request_.get(), &flag, &status));

    if (!flag) {  // Request not complete
      if (*comm_type_ == BuffCommType::sender) {
        PARTHENON_MPI_CHECK(MPI_Wait(my_request_.get(), MPI_STATUS_IGNORE));  // BLOCKS!
      } else {
        PARTHENON_MPI_CHECK(MPI_Cancel(my_request_.get()));  // Cancel receive
        PARTHENON_MPI_CHECK(MPI_Wait(my_request_.get(), MPI_STATUS_IGNORE));  // BLOCKS!
      }
    }
  }
#endif
}
```

### Why `boundary_comm_map.clear()` is Expensive

1. Each rank has ~200 communication buffers (boundary exchange channels with neighbors)
2. During AMR redistribution, mesh blocks move between ranks
3. Ranks receiving new blocks must clear their old communication state
4. `clear()` calls destructor on each `CommBuffer`
5. Each destructor potentially calls `MPI_Wait()` - **blocking**
6. Serialized blocking waits accumulate to 70-84ms

### Evidence: MPI Message Volume

```
Per timestep:
- MPI_Irecv: ~765,000 calls
- MPI_Isend: ~765,000 calls
- Per rank average: ~187 communication channels
```

## Why It Appears Random

1. AMR runs every ~10 timesteps to rebalance computational load
2. The load balancer decides which mesh blocks to move based on work imbalance
3. Ranks that **receive new blocks** must clear old buffers (trigger the expensive Clear)
4. As simulation physics evolve, different regions become hot/cold
5. Different ranks need block redistribution each time → different stragglers

## Complete Control Flow to Offending MPI_Wait

```
driver.cpp:109
└── pmesh->LoadBalancingAndAdaptiveMeshRefinement(tm.ncycle, pinput, app_input)

amr_loadbalance.cpp:59-111
└── Mesh::LoadBalancingAndAdaptiveMeshRefinement()
    ├── Kokkos::pushRegion("LoadBalancingAndAdaptiveMeshRefinement")
    ├── UpdateMeshBlockTree()           // Check refinement needs
    ├── GatherCostListAndCheckBalance() // Gather load info
    └── RedistributeAndRefineMeshBlocks(pin, app_in, nbtotal)  [line 91/96/102]

amr_loadbalance.cpp:502-976
└── Mesh::RedistributeAndRefineMeshBlocks()
    ├── Kokkos::pushRegion("RedistributeAndRefineMeshBlocks")
    ├── Step 1: Construct new block list
    ├── Step 2: CalculateLoadBalance()      // Decide block→rank mapping
    ├── Step 3: Count send/recv blocks
    ├── Step 4: Calculate buffer sizes
    ├── Step 5: Allocate buffers
    ├── Step 6: MPI_Irecv for incoming blocks
    ├── Step 7: Pack and MPI_Isend outgoing blocks
    ├── Step 8: MPI_Waitall for receives, unpack
    ├── Step 9: Update block_list, rebuild tree
    └── Initialize(false, pin, app_in)      [line 972]

mesh.cpp:1104-1123
└── Mesh::Initialize()
    └── Kokkos::pushRegion("Mesh::Initialize::BuildAndPost")  [line 1104]
        ├── Kokkos::pushRegion("Mesh::Initialize::BuildAndPost::Clear")  [line 1106]
        │   └── ClearCommBuffers_bad(num_partitions)  [line 1107]
        ├── Kokkos::popRegion()  // Clear  [line 1108]
        ├── BuildBoundaryBuffers()   // Rebuild comm channels
        └── StartReceiveBoundaryBuffers()

mesh.cpp:1245-1248
└── Mesh::ClearCommBuffers_bad()
    ├── boundary_comm_map.clear()       ← TRIGGERS DESTRUCTORS
    └── boundary_comm_flxcor_map.clear()

communication_buffer.cpp:45-74
└── ~CommBuffer<T>()   // Called ~200 times per rank
    ├── if (my_request_.use_count() == 1)  // Last reference
    │   ├── MPI_Test(my_request_, &flag, &status)  // Check if complete
    │   └── if (!flag)  // Request NOT complete
    │       ├── if (sender): MPI_Wait(my_request_, ...)   ← BLOCKS 70-84ms
    │       └── else: MPI_Cancel() + MPI_Wait(...)        ← BLOCKS
```

### Why the Wait Blocks for 70-84ms

The `boundary_comm_map` contains communication channels for boundary exchange between neighboring mesh blocks. When a rank receives **new** mesh blocks during AMR redistribution:

1. Old neighbor relationships are invalid
2. `clear()` destroys all CommBuffers for old boundaries
3. Some buffers have **pending sends** (MPI_Isend posted but peer hasn't received)
4. Destructor calls `MPI_Wait()` to ensure send completes before freeing buffer
5. The peer (receiving rank) may not have posted its `MPI_Irecv` yet → **blocks**

The 70-84ms duration is the time for the slowest peer to finish its work and post the matching receive.

## Empirical Proof (Flow 3: MPI Wait Stats)

The hypothesis was proven by correlating Clear events with aggregated MPI_Wait statistics per rank:

### Key Finding: Clear Duration = MPI_Wait Duration

```
Timestep 584, SWID 3193:
  rank=2318: Clear=81.9ms, wait_cnt=79, total_wait=81.5ms, max_wait=81.5ms

  Correlation: 81.9ms Clear ≈ 81.5ms MPI_Wait total (99.5% match)
```

### Clear vs Non-Clear Ranks Comparison

| Metric | Clear Rank (2318) | Other Ranks (n=4095) |
|--------|-------------------|----------------------|
| wait_cnt | 79 | 92 (avg) |
| total_wait_ns | 81.5ms | 0.0ms (avg) |
| max_wait_ns | 81.5ms | - |

### Critical Insight: One Blocking Wait Dominates

```
max_wait / total_wait = 81.5ms / 81.5ms = 100%
```

This proves that **a single MPI_Wait call blocks for the entire duration**. The destructor hits one incomplete send/receive and blocks until the peer completes its side of the communication.

### Why Non-Clear Ranks Have 0ms Wait Time

Non-Clear ranks call MPI_Wait on already-completed requests (from normal boundary exchanges). These return immediately. Clear ranks call MPI_Wait on **incomplete** requests from communication channels being torn down - the peer may not have issued its matching receive/send yet.

## Metrics

| Metric | Value |
|--------|-------|
| Total ranks | 4096 |
| Buffers per rank | ~200 |
| Ranks with Clear per timestep | 1-11 (0.0-0.3%) |
| Clear duration | 70-84ms |
| Collective spread (anomalous) | 50-115ms |
| Collective spread (normal) | 0.36ms median |
| AMR frequency | ~every 10-11 timesteps |

## The Straggler Pattern

```
Timestep N (AMR runs):
  T+0:    LoadBalancingAndAdaptiveMeshRefinement starts
  T+10ms: Load balancer decides block redistribution
  T+20ms: Blocks packed and sent (Step 7)
  T+30ms: Most ranks receive/unpack - fast path (no Clear needed)
  T+30ms: Fast ranks hit MPI_Allreduce, start waiting...

  T+30-110ms: 1-11 ranks call boundary_comm_map.clear()
              → 200 CommBuffer destructors
              → 200 potential MPI_Wait() calls
              → BLOCKING for 70-84ms

  T+110ms: Slow ranks finish Clear, hit MPI_Allreduce
  T+110ms: Collective completes (4000+ ranks waited 80ms!)
```

## Why Only Some Ranks Need Clear

Looking at the data:
- 114 unique ranks had Clear events across 187 timesteps
- These ranks are receiving **new mesh blocks** after redistribution
- They need to tear down old neighbor communication channels
- Ranks keeping their blocks skip this entirely

## Recommendations

1. **Non-blocking cleanup**: Instead of `MPI_Wait()` in destructor, queue requests for later completion or use `MPI_Request_free()`

2. **Amortize cleanup**: Clear buffers incrementally over multiple timesteps rather than all at once

3. **Async cancel**: Use `MPI_Cancel()` without blocking wait where possible

4. **Overlap with computation**: Start clearing old buffers while new blocks are still being received

5. **Buffer pooling**: Reuse communication buffers instead of destroying/recreating them

## Flows Used

1. `0-probe-counts.yaml` - Initial probe discovery
2. `1-baseline-collectives.yaml` - MPI collective tracking
3. `2-straggler-hunt.yaml` - Kokkos events >1ms + collective raw data
4. `3-mpi-wait-stats.yaml` - Aggregated MPI_Wait stats per rank/swid (empirical proof)

## Files Analyzed

- `parthenon/src/mesh/mesh.cpp:1104-1248` - Mesh initialization and ClearCommBuffers_bad
- `parthenon/src/utils/communication_buffer.cpp:45-74` - CommBuffer destructor with MPI_Wait
- `parthenon/src/utils/communication_buffer.hpp:42-126` - CommBuffer class definition
