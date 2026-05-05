# Build Packet - HX-04 / T-2.3 / kernel-runtime-policy

## Task ID

HX-04-T-2.3-kernel-runtime-policy

## Objective

Add retry ceilings, loop-cap rules, and blocked disposition output to the shared HX-04 kernel contract without widening into durable state ownership.

## Minimum Change

- extend `KernelContract` with the explicit retry ceiling and active/passive loop caps already assumed by the watch-loop contract
- expose one actionable blocked disposition output that carries blocked status, exit code `90`, residual output name, and the risk-accept follow-up command
- add focused unit tests for the new runtime-policy fields on the shared kernel contract

## Verification

- `uv run pytest tests/unit/test_kernel_contract_runtime_policy.py -q`