# Implementation Details

```js
console.log('hello world')
```

## Setup a repo

1. Set up a `mon-umbrella`
2. Set up a `monsvc`
3. Add cmake modules and snippets for `duckdb`, `arrow`, maybe `parquet`, eventually `datafusion`, `flatbuffers` etc. (Flatbuffers is a serialization library, needn't go into the umbrella, but some instructions could.)

### Directory Structure

```
monsvc
|- src
   |- common
   |- preload
   |- aggregator
   |- controller
|- snippets
|- benchmarks
|- tests
CMakeLists.txt
```

## Things to think

1. How should the telemetry flavor of SQL look? It should have some ETL semantics.
2. Can you combine multiple telemetry query plans and co-optimize them?
3. Handshaking protocol spec - reference implementations for state management etc.
4. A reference usecase for CUDA/CUPTI.

# "Spec"

## Keywords

Keword | Desc
-------|-----
`SBOT` | Shuffle-based overlay for telemetry  (the more complicated topology we are trying to setup with controller + aggregators)
`3HOP` | Pre-existing subset of SBOT that exists in the MPI app domain. Has the standard SRC-SRCREP-DESTREP-DEST paths.
`3HOP-C` |  Control path of the 3HOP topology. Currently implemented as a separate instance of the shuffler with zero buffering.
`3HOP-D` | Data path of the 3HOP topology. (Queues with large buffers)

## Components

### `deltafs-nexus`
Currently, does two things that we are planning on decoupling.

1. Interacts with Mercury, generates some notion of a `handle` that shuffler understands
2. Generates a 3hop topology using the MPI communicator

SBOT functionally needs:

1. The underlying layer to bootstrap with or without MPI
2. The underlying layer to support point-to-point communication

### Mercury Notes

### Mercury RPC

To obtain the target's "address" (in the libfabric/PSM domain):

1. Target calls `HG_Addr_self`
2. Target calls `HG_Addr_to_string`
3. Out-of-band exchange of string
4. Origin calls `HG_Addr_lookup` to register the target from the string

Initiating an RPC (origin, application thread):

1. `HG_Register_name` registers an RPC function, with serdes.
2. `HG_Create` creates a single RPC call instance.
3. `HG_Forward` actually launches it.

Remote, progress thread: `HG_Respond`

`HG_Progress`: makes progress

`HG_Trigger`: initiates the completion callbacks from the application thread (if it's not a one-way RPC)

### Mercury Bulk

Uses RMA to transfer data. 

? `mercury-progressor`?

We plan on using a control interface and regular Socket I/O to do this exchange

### What we want from Nexus and Shuffle

1. The default 3hop topology being intact, but optional
2. A mechanism to add p2p endpoints and queues for them (if a queue exists because of 3hop, this is a no-op)

## Bootstrapping

MPI application and the monitoring service initialize separately and handshake. The monitoring service has two components: controller (`CTRL`), and aggregators (`AGG0`...`AGGk`). Each of monitoring components corresponds to a separate node.

The application has three types of ranks:

1. Rank 0: Lead rank of the simulation, has a special channel with the controller
2. SRC ranks: all ranks in the simulation (`nnodes` * `nperrank`).
3. SRCREP ranks: lead rank on each node (total: `nnodes` SRCREP ranks).

Rank 0 is initialized with the controller's control network IP address, via an environment variable. All aggregators also know their controller. Aggregators independently handshake with the controller. Maybe the controller knows how many aggregators to expect and sends a list to Rank 0 when they've all bootstrapped.

Rank 0 broadcasts the list to all ranks via `3HOP-C`. All `SRCREP` ranks _establish connections_ with all aggregators.

**Note**: There's no such thing as establishing a connection in Mercury. With Verbs, you could maintain a `RC QP` to each aggregator, post large messages to the queue, and let the rest be automatically managed. Not sure if Mercury Bulk allows something like that, or if it makes a significant difference. A new QP for each RPC sounds expensive?

# DataFusion Notes

## DataFusion Ray

Converts logical plan first to a physical plan, and then to a distributed physical plan. The distributed plan generation relies around the presence of `ReparttitionExec`, `CoalesceExec`, or `SortPreservingMergeExec`. Branch `main` as of Nov 11, 2024 relies exclusively on Ray to do the shuffling. There's a legacy shuffler in older code that materializes intermediate output to disk.

### Distributed Query Execution

`ExecutionPlan` is converted into `ExecutionGraph`. `ExecutionGraph` is `map<int, QueryStage>` indexed by `stage_id: int`. `QueryStage` seems to be a wrapper over `ExecutionPlan`. The final `QueryStage` is always supposed to have one partition as output.

### Legacy Shuffler Code

URL: https://github.com/apache/datafusion-ray/tree/b91705c3e5ddc2f25d630ee8e75fbbb5f6ae0099

Has `ShuffleWriterExec` and `ShuffleReaderExec`. The `Exec` classes support the trait `ExecutionPlan` and so implement an `execute` API.

Examples: https://github.com/apache/datafusion/tree/main/datafusion-examples/examples

## DataFusion Ballista


## Name: ROME

Realtime Observability and Management Engine?
Online Feedback and Aggregation

Realtime Feedback and Observability via On-Fabric Aggregation
Online Aggregation, Control, and Feedback
Realtime Feedback and Control via On-fabric Aggregation
FLOP: Feedback Loop for Online Performance
ROCA: Realtime Online Control and Aggregation
Aggregation Plane for Interactive Control
CAPO: Control and Aggregation Plane for Observability
Interactive Ob
Online Control and Aggregation Interface
Aggregation for Rapid Feedback
Aggregating Overlays
Overlays for Online Feedback
EPIC: Extensible Plane for Interactive Control


name: EPOC: Extensible Planes for Observability and Control

Online Control and Observability Plane

Aggregation Planes for Telemetry and Interactive Control

Aggregating Overlays for Realtime Observability and Control

# Spec: Bootstrapping

The goal of bootstrapping is for the leadrank to have the "mercury address" of the controller and the aggregators. For now, the mercury address is just some made-up string ("helloworld-ctrl"...). The initial setup will be simple, but we will write the code in a way that we are able to make things complex over time. We will initially have three binaries.

1. LeadRank: The code that runs on Rank 0 of a MPI simulation. 
2. Aggregator: A single aggregator (later there will be more).
3. Controller: A single controller.

## Step 1: 3 binaries, hello-world

```
root
|- src
   |- common // for utilities, logging etc.
   |- libmon
      |- aggregator 
         |- aggregator.h
      |- controller
         |- controller.h
      |- leadrank
         |- leadrank.h
|- tools
   |- aggregator_main.cc
   |- controller_main.cc
   |- leadrank_main.cc
|- scripts
```

Define just the binaries with "hello world - aggregator/controller/lead rank". Write a script to launch them using mpirun. If you run the mvapich mpirun, you get a parameter `$PMI_RANK`.

The idea is to run `./launch.sh` and it will run `mpirun -np 3 launch_inner.sh`, and launch_inner.sh will conditionally execute one of the three depending on the value of PMI_RANK. This will enable us to initially build things using a single node.

By the end, you should see three hello-worlds from each binary.

## Step 2: dependencies

We want to link this to pdlfs-common. pdlfs-common has the `Env` abstraction. We want to use the Mutex, MutexLock, and ConditionVariable wrappers from pdlfs-common.

This would be a useful reference (for reference, this repo implements the CARP query client --- it is a single-node multithreaded tool that reads SSTs using the Env interface and merges them and computes a range query.): https://github.com/anku94/carp/tree/master/src/reader

We also want to use `flatbuffers` for message types, but that can come later.

`Env` also has a thread pool but we do not want to use it.

## Step 3: get basic TCP-based communication going on

The controller opens a standard TCP socket and binds to a 10.111 address at a known port, and listens.

Both leadrank and aggregator get the address:port as environment variables. To begin with let's implement the leadrank-controller path. Aggregator just prints helloworld.

leadrank tries to connect to the controller address (which may fail because the controller may not be active yet. for fun we can add a sleep 5 script to delay the controller start to test this). it retries 3 times, 1 second apart, and gives up if it can not. If it can, exchange basic hellos.

## Step 4: get threading right

on leadrank (and later aggregator), the TCP client is in a separate pthread (call it BootstrapService let's say). The main thread is essentially waiting on a condition variable for the bootstrap service to complete handshaking and tell the main thread to proceed.

on the controller, first, there is a separate thread for the server, and then there is a separate thread for all active connections. (you call poll_all or something on all FDs).

## Step 5: implement a protocol using flatbuffers

the flow we essentially want to implement is:

- leadrank reaches out to controller (retry N times, then give up)
- leadrank asks controller for some BootstrapInfo message type
- controller can either say NOT_READY or return the packet
- as long as controller says NOT_READY leadrank keeps trying
- controller becomes ready once the aggregator has established a connection and given the controller its mercury address (for now mercury address is some string helloworld)
- controller returns a list of all aggregators and their mercury addresses to the leadrank
- leadrank BootstrapService wakes up main thread
- main thread terminates
- controller and aggregator are manually terminated

We want to implement this in a way that the controller expects K aggregators to reach out, says NOT_READY until all of them do, eventually succeeds, and sends relevant state to leadrank.

All protocol communication happens using flatbuffers. Each message has an opcode identifying it. Some HandleMessage call multiplexes on the basis of that. Optional: use chatgpt and other codebases to identify how bootstrapping and communication are typically structured for inspiration.

See how much code can be shared and how much is specific to each of the three components. Use pdlfs::Logger and wrappers over that. I use it with glog, this may be a useful reference:

https://github.com/anku94/amr/blob/main/tools/common/common.h

### Style Guidelines

- Have a .clang-format with BasedOnStyle: Google and use Google style conventions (like all our code does.)