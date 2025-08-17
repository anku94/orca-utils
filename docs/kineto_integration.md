# Kineto Integration Notes

Refer to [kineto_walk_through](./kineto_walk_through.pdf) for a context of how kineto is structured.

## PyTorch Kineto Client Callbacks
The way PyTorch Kineto interacts with Libkineto is by registering Libkineto's client callbacks, particularly `start()` and `stop()`, which are called when Libkineto starts and stops tracing in the daemon mode.

Specifically, PyTorch side's `enableProfiler()` gets called in the `start()` callback and `disableProfiler()` gets called in `stop()`. These are the two key functions that are related to PyTorch side's CPU tracing etc. We will dive into them in below.

## Important classes
`KinetoThreadLocalState`: The key class that manages CPU tracer's operations. It's thread local in the frontend mode and is shared/global in the daemon mode.

`RecordQueue`: Used to retrieve captured CPU traces. It itself does not store the traces, which are actually done by `ThreadLocalSubqueue`, but instead it acts more like a manager. It can also get Python traces, but only if `with_stack` profiling option is enabled. It's a member of `KinetoThreadLocalState`.

`ThreadLocalSubqueue`: The actual class that captures CPU traces. It has various kinds of events, such as `op_events_` which denotes tensor operations in ATen, `kwinputs_` and `inputs_outputs_` if the user wants to capture the input shapes, `allocations_` for memory operations, `py_calls_` for python stacks etc.

`Result`: A wrapper of the raw events. The retrieved events from the `ThreadLocalSubqueue` are saved to a vector of `Result` before further processing.

`activity_t`: Basically an equivalent of `Result` that Libkineto speaks. `Result` will be used to construct a corresponding `activity_t` when sending to Libkineto.

## How does Kineto capture CPU traces?
When `enableProfiler()` gets called, Kineto creates a global `KinetoThreadLocalState` and sets profiling callbacks (on function enter and exit) for ATen functions, which will push the event to the `ThreadLocalSubqueue`.

When Kineto needs to retrieve the captured events in `disableProfiler()`, it removes the previously registered profiling callbacks and drains various events from the `ThreadLocalSubqueue`. It then processes the events and calls `addKinetoEvents()` to pass them to Libkineto. After that, it clears relevant data structures.

## What modifications do we need?
1. First of all, we don't want to unregister the profiling callbacks when retrieving the events, although the overhead of callback registration seems not much?
2. We need to make the trace processing logic independent, i.e. we will have many processing threads running simultaneously and they can't intefere with each other. This is similar to what we did in Libkineto by moving the relevant data structures to a snapshot so that the processing logic only cares about local data. We don't need to clear any data when it's done for the same reason.
3. To implement 2, we need to identify which data structures are needed and accessed during the processing logic.

## How am I planning to approach this?
The below is the pseudo workflow of how I planned to do the hack.

Original workflow of retrieving CPU traces:
```
disableProfiler() (entry point)
-> RecordQueue::getRecords()
->-> (1) drain various kinds of raw events from the `ThreadLocalSubqueue` queue and save them in a vector of `Result`.
->-> (2) call addKinetoEvents() to pass the traces to Libkineto.
->-> (3) process the traces. e.g. set up relative orders, parentness, etc.

-> materializeOpEvents(): further loop through the traces and make some parsing there, i.e. setting up relevant metadata of the trace records.
```

Note that it seems `addKinetoEvents()` should be the last thing and processing CPU traces after passing them to Libkineto doesn't make sense, but since there are pointers to the `activity_t` events from `Result`, the `activity_t` saw by Libkineto will still get modified in functions like `materializeOpEvents()`, which essentially are adding certain matadata to the trace records.

The new workflow:
```
disableProfiler() (entry point)
-> (1) makeSnapshot(): New added function. Create a snapshot struct, which saves the raw events from the queue and contains relevant data structures needed to process the events.
-> (2) addKinetoEventsWithCallback(): New added function. Besides addKinetoEvents(), it passes a lambda function as a callback to Libkineto, which encapsulates all trace processing logics against the snapshot.
```

The key ideas here are:

1. Use the snapshot mechanism to decouple the trace processing logic from the actual PyTorch class so that they can be executed simultaneously.
2. Since the trace processing happens in Libkineto's context, we need to wrap up related functions into a single callback and pass it to Libkineto along with the snapshot, so that it can be executed in the thread launched by Libkineto without blocking the main thread.

Note the above is a reflection a rough roadmap. Subtle things might change while I keep implementing it.