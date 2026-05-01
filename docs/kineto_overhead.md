# Notes on PyTorch Kineto's overhead

Basically there are two ways of enabling Kineto traces in PyTorch programs: 1. PyTorch's API; 2, Dynolog.

Below is a quick code path walk through of these two approaches.

## PyTorch's Profiler API
With PyTorch's API we typically have a `schedule` for the profiler routine which specifies the number of warmup and record steps etc. Note the below phases are entered implicitly when we call `profiler.step()` based on its current state.

When the profiler is entering the `warmup` phase, the python code calls `_prepare_profiler()` which is a Cpp stub function `prepareProfiler()`. At the leaf it calls `libkineto_init()` to initialize kineto resources including CUPTI etc. **Note** that CUPTI starts tracing now, but it's just traces collected at this phase will be dropped later.

Code path:
> -> _prepare_trace() (python)
>
> -> prepareProfiler() (cpp stub)
>
> -> prepareTrace() (kineto_shim.cpp)
>
> -> libkineto_init() (libkineto's api)
>
> -> ActivityProfilerProxy::prepareTrace() (same level as libkineto_init)
>
> -> ActivityProfilerController::prepareTrace() (stop ongoing profiler if any)
>
> -> CuptiActivityProfiler::configure() (parse the profiling config and set up cupti interfaces accordingly. change current state to `Warmup`)

After the warmup phase the profiler enters the recording phase, at which time python's `start_trace()` is called and further cpp stub `enableProfiler()`. This call just marks the timestamp when the actual tracing is enabled so that the traces collected in the warmup phase won't be processed later.

Code path:
> -> _KinetoProfile::start_trace() (python)
> 
> -> profile._start_trace() (python)
> 
> -> _enable_profiler() (python)
> 
> -> enableProfiler (cpp stub)
> 
> -> startTrace (kineto_shim.cpp)
> 
> -> ActivityProfilerProxy::startTrace()
> 
> -> ActivityProfilerController::startTrace()
> 
> -> CuptiActivityProfiler::startTrace()
> 
> -> CuptiActivityProfiler::startTraceInternal() (set start time for capturing traces, change current state to `CollectTrace`)

When the profiler has collected the specified number of steps, it should stop the tracing and parses collected events. This will take most of the time, especially if specifying a large number of steps to trace.

Code path:
> ->_KinetoProfile::stop_trace() (python)
> 
> -> _disable_profiler() (python)
> 
> -> disableProfiler (cpp stub)
> 
> -> KinetoThreadLocalState::finalizeTrace()
> 
> -> materializeOpEvents() (called in the same level as `getRecords()` but after that. it for loops all events and does some parsing there.)
> 
> -> RecordQueue::getRecords()
> 
> -> addKinetoEvents()
> 
> -> stopTrace() (kineto_shim.cpp)
> 
> -> ActivityProfilerProxy::stopTrace()
> 
> -> ActivityProfilerController::stopTrace()
> 
> ->-> 1) CuptiActivityProfiler::stopTrace()
> 
> ->-> stopTraceInternal() (disable cupti resources, set the end time for capture and state to `ProcessTrace`)
> 
> ->-> 2) CuptiActivityProfiler::processTrace()
> 
> ->-> processTraceInternal() (process all collected traces in memory and reset the profiler)

So the above is the main code path of these different profiler phases. Whenever a profiling window is done (including warmup and recording and `stop_trace()` is called), the user registered callback is called, where we can save the events into Chrome JSON.

Note that if we don't explicitly access the trace events using `profiler.events()`, there will be no cpp-python data exchanges -- all data resides in cpp side. The flushing stuff is handled purely in cpp too.

Also note that if we set the profiler to emit data after every step (i.e. #warmup=0, #active=1), all the three major APIs will be called at the same time when `profiler.step()` is called, and because they're synchronous and `disableProfiler()` is expensive, it will incur a significant overhead to the pytorch program, even if we do nothing in the user callback.

If we don't use the `schedule()` but simply run the profiler when the training starts and terminate it when the training finishes, the code path will be the same but `_prepare_profiler()` and `_enable_profiler()` will be called in the beginning and `_disable_profiler()` will be called in the end, and there is no need to call `profiler.step()` then.

## Dynolog API
When we launch the pytorch program, we can let it know we'll use dynolog by setting the env variable `KINETO_USE_DAEMON=1`, i.e. the daemon mode. Then we don't need to do any modification to the pytorch program, i.e. there will be no profiler-related code.

The magic behind this is that pytorch registers a hook after `optimizer.step()` as optimizer is always the last thing in a step to update the model's weights using gradients. It's just similar to calling `profiler.step()` to keep the profiler informed of the current step but pytorch does this for us.

When the pytorch program is launched, it knows kineto is running in the daemon mode and as such it spawns up a thread to poll any command (they call it config) sent from dynolog and start tracing dynamically. At this time, it also initializes kineto resources by `libkineto_init()`.

There are timestamp and step based profiling, here we focus on the latter. The key function is `performRunLoopStep()`, which is preriodically called in a loop from a dedicated thread `profilerLoop()` that is spawned only in the daemon mode. Note `performRunLoopStep()` can also get called within `optimizer.step()` as mentioned below.

When `optimizer.step()` is called, in cpp it's `profilerStep()` and further `ActivityProfilerController::step()`, where it increments the current step counter in cpp and handles the profiling state machine discussed above via `CuptiActivityProfiler::performRunLoopStep()`.

Within `ActivityProfilerController::step()`, if current step > warmup step, it configures the profiler accordingly to start collecting traces. *This calls the same function as what prepareTrace() does, i.e. `CuptiActivityProfiler::configure()`.*

If current step > start step, it goes to the `RunloopState::Warmup` switch case in `performRunLoopStep()`, where it calls `startTraceInternal()` in the end. So this is still the same function the pytorch API calls.

If current step > end step, it goes to the `RunloopState::CollectTrace` switch case in `performRunLoopStep()` to stop the profiler and collect traces. Because this is a time-consuming operation, to avoid blocking the pytorch program it **launches a separate thread** to call `stopTraceInternal()`, still the same function that pytorch's API calls.

To process the traces, for example writing to json, it goes to the `RunloopState::ProcessTrace` case and calls `processTraceInternal()`. This is also an expensive operation, but since it's not called directly within `profilerStep()` but in the dedicated thread that runs `performRunLoopStep()` periodically, it won't block the pytorch program either.


## Summary & Thoughts
- PyTorch's profiler and dynolog call the same underlying code, but all code paths are synchronous with PyTorch's API and multi-threaded with dynolog, so it appears dynolog incurs much lower overhead w.r.t. the pytorch program's performance.
- Now that we know we can't avoid the long time taken by stopping the profiler and processing the traces anyways, should we still opt to emitting per-step traces? Using another thread probably won't help here, because trace collection can't happend unless the current tracing routine is done.
- Maybe we can reduce the overhead by emitting traces for K steps where K > 1? This way the stopping and processing will happen only per K steps instead of 1, but my concern is the time for processing traces may scale with the number of collected traces. So if say processing a single step takes 0.5s and processing 4 steps takes 1.8s, setting K = 4 doesn't change a lot...