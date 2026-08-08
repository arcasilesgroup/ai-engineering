# Performance

- Complexity of the loop that grows with data, and what n actually is in production.
- Queries inside loops, and reads that could be one read.
- Anything on a hot path measured in milliseconds: a slow control is a disabled control.
- Memory held for longer than the request that needed it.
- Caches: what invalidates them, and what happens on a miss storm.
- Measure before claiming. "This is faster" without a number is a preference.
