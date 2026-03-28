# Handler: PyTorch Runtime Error Resolver

## Purpose

Resolves PyTorch runtime errors including tensor shape mismatches, device placement conflicts, CUDA out-of-memory failures, autograd graph issues, and DataLoader collation problems. This handler addresses runtime errors, not Python compilation or import errors (use `python-build.md` for those). Focuses on the numerical and computational aspects specific to deep learning: shape algebra, memory management, gradient flow, and device consistency. Targets PyTorch 2.0+ with CUDA 11.8+.

## Activation

Activate this handler when:

- The project imports `torch`, `torchvision`, `torchaudio`, or `torch.nn`
- Runtime errors reference `RuntimeError` with tensor-specific messages (shapes, devices, dtypes)
- The user reports CUDA OOM, gradient errors, or DataLoader failures
- Model training produces `NaN` or `Inf` values, or loss does not decrease

## Diagnostic Sequence (Phase 2 -- Reproduction)

Run these commands in order. Stop at the first failure and diagnose before continuing.

```bash
# 1. Verify PyTorch installation and CUDA availability
python -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'cuDNN version: {torch.backends.cudnn.version()}')
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'GPU memory: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB')
else:
    print('Running on CPU only')
"

# 2. Check for basic tensor operations
python -c "
import torch
x = torch.randn(2, 3)
y = torch.randn(3, 4)
z = x @ y
print(f'Basic matmul OK: {x.shape} @ {y.shape} = {z.shape}')
"

# 3. Verify model can be instantiated (adjust import to match project)
python -c "
import sys; sys.path.insert(0, '.')
# from model import YourModel
# model = YourModel()
# print(f'Model parameters: {sum(p.numel() for p in model.parameters()):,}')
print('Uncomment model import to test instantiation')
"

# 4. Test with minimal batch size
python -c "
import torch
# Replace with actual model and data shape
batch_size = 2
x = torch.randn(batch_size, 3, 224, 224)
print(f'Test tensor shape: {x.shape}')
print(f'Test tensor device: {x.device}')
print(f'Test tensor dtype: {x.dtype}')
"

# 5. Check GPU memory status (if CUDA available)
python -c "
import torch
if torch.cuda.is_available():
    print(f'Memory allocated: {torch.cuda.memory_allocated() / 1e6:.1f} MB')
    print(f'Memory reserved: {torch.cuda.memory_reserved() / 1e6:.1f} MB')
    print(f'Max memory allocated: {torch.cuda.max_memory_allocated() / 1e6:.1f} MB')
"

# 6. Run the failing training/inference script with batch_size=2
# python train.py --batch-size 2 --epochs 1 2>&1
```

## Error Table (Phase 3 -- Root Cause)

| Error | Cause | Fix |
|-------|-------|-----|
| `RuntimeError: mat1 and mat2 shapes cannot be multiplied (AxB and CxD)` | Matrix multiplication where the inner dimensions do not match (B != C). Common when the linear layer input size does not match the flattened feature map. | Print shapes before the operation: `print(x.shape)`. Calculate the correct input size: for Conv2d output going into Linear, the size is `channels * height * width` after all convolutions and pooling. Use `x.view(x.size(0), -1)` to flatten. |
| `RuntimeError: Expected all tensors to be on the same device, but found at least two devices, cuda:0 and cpu` | A tensor or model parameter is on a different device than the input. Common when forgetting to move the model or data to GPU. | Move the model: `model.to(device)`. Move the data: `x = x.to(device)`. Define `device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')` once and use consistently. Check that all tensors in loss computation are on the same device. |
| `torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate X MiB` | GPU memory exhausted. Batch size too large, model too large, or memory leak from accumulated gradients/tensors. | Reduce batch size. Use `torch.cuda.empty_cache()`. Enable gradient checkpointing: `model.gradient_checkpointing_enable()`. Use mixed precision: `torch.cuda.amp.autocast()`. Use `with torch.no_grad():` during evaluation. Check for tensors not detached in logging. |
| `RuntimeError: element 0 of tensors does not require grad and does not have a grad_fn` | Calling `.backward()` on a tensor that was created without gradient tracking (detached or created with `requires_grad=False`). | Ensure the computation graph is connected. Do not detach intermediate results. Check that model parameters have `requires_grad=True`. Verify loss is computed from model output, not from detached copies. |
| `RuntimeError: one of the variables needed for gradient computation has been modified by an inplace operation` | An in-place operation (e.g., `x += 1`, `x.relu_()`, `x[0] = val`) modified a tensor needed for backward pass gradient computation. | Replace in-place operations with out-of-place equivalents: `x = x + 1` instead of `x += 1`. Use `F.relu(x)` instead of `x.relu_()`. Clone before modifying: `x = x.clone()`. |
| `RuntimeError: default_collate: batch must contain tensors, numpy arrays, numbers, dicts or lists; found <class 'X'>` | The DataLoader's default collate function cannot handle a custom data type returned by the Dataset's `__getitem__`. | Implement a custom `collate_fn` that handles the data type. Convert to tensors in `__getitem__`. For variable-length sequences, pad in the collate function. |
| `RuntimeError: Trying to backward through the graph a second time` | Calling `.backward()` twice on the same computation graph without `retain_graph=True`. Common in GANs and multi-loss training. | Add `retain_graph=True` to the first `.backward()` call if a second backward is needed. Alternatively, restructure to avoid reusing the graph. For most cases, detach intermediate results. |
| `IndexError: index out of range in self (Embedding)` | An input index to `nn.Embedding` exceeds `num_embeddings - 1`, or a negative index is passed. | Check the vocabulary size matches `num_embeddings`. Verify tokenizer output range: `assert input_ids.max() < embedding.num_embeddings`. Check for padding token index. Print `input_ids.min()` and `input_ids.max()` before the embedding layer. |
| `RuntimeError: expected scalar type Float but found Double` | Tensor dtype mismatch. NumPy defaults to float64 (Double), PyTorch expects float32 (Float). | Convert tensors: `x = x.float()` or `x = x.to(torch.float32)`. When creating from NumPy: `torch.from_numpy(arr).float()`. Set NumPy default: `arr = arr.astype(np.float32)`. |
| `RuntimeError: Given groups=1, weight of size [X], expected input[Y] to have Z channels` | Conv2d input channels do not match the layer's `in_channels` parameter. | Verify input shape is `(batch, channels, height, width)`. Check that the channel dimension matches `in_channels`. For grayscale images, use `in_channels=1`. For RGB, use `in_channels=3`. |
| `ValueError: optimizer got an empty parameter list` | `model.parameters()` returned an empty iterator. Model has no trainable parameters or was not properly defined. | Verify `nn.Module` subclass registers parameters via `nn.Linear`, `nn.Conv2d`, etc. (not plain tensors). Use `nn.Parameter()` for custom parameters. Check that `self.layers = nn.ModuleList([...])` is used, not a plain Python list. |
| `RuntimeError: stack expects each tensor to be equal size, but got [X] at entry 0 and [Y] at entry 1` | DataLoader is trying to batch tensors of different sizes (variable-length sequences, different image sizes). | Implement a custom `collate_fn` with padding. Use `torch.nn.utils.rnn.pad_sequence()` for sequences. Resize images to a consistent size in the transform pipeline. |

## Shape Debugging Section

```python
# Add shape debugging hooks to a model
def register_shape_hooks(model):
    """Print input and output shapes for every layer."""
    def hook_fn(module, input, output, name=""):
        input_shapes = [x.shape if isinstance(x, torch.Tensor) else type(x) for x in input]
        output_shape = output.shape if isinstance(output, torch.Tensor) else type(output)
        print(f"{name:40s} | input: {input_shapes} | output: {output_shape}")

    for name, layer in model.named_modules():
        layer.register_forward_hook(lambda m, i, o, n=name: hook_fn(m, i, o, n))

# Usage:
# register_shape_hooks(model)
# output = model(sample_input)  # prints all shapes
```

```python
# Manual shape tracing through a forward pass
def trace_shapes(model, x):
    """Step through the forward pass printing shapes."""
    print(f"{'Layer':40s} | {'Output Shape':20s} | {'Params':>10s}")
    print("-" * 75)
    for name, layer in model.named_children():
        x = layer(x)
        params = sum(p.numel() for p in layer.parameters())
        print(f"{name:40s} | {str(x.shape):20s} | {params:>10,}")
    return x
```

```bash
# Quick shape check from command line
python -c "
import torch
from model import YourModel  # adjust import

model = YourModel()
x = torch.randn(2, 3, 224, 224)  # adjust shape

# Trace through the model
try:
    with torch.no_grad():
        output = model(x)
    print(f'Input:  {x.shape}')
    print(f'Output: {output.shape}')
except RuntimeError as e:
    print(f'Shape error: {e}')
    # Print all named module dimensions
    for name, param in model.named_parameters():
        print(f'  {name}: {param.shape}')
"
```

## Memory Debugging Section

```python
# Monitor GPU memory during training
def print_memory_stats(tag=""):
    """Print current GPU memory usage."""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        reserved = torch.cuda.memory_reserved() / 1e9
        max_alloc = torch.cuda.max_memory_allocated() / 1e9
        print(f"[{tag}] Allocated: {allocated:.2f} GB | Reserved: {reserved:.2f} GB | Peak: {max_alloc:.2f} GB")
```

```python
# Find the largest tensors in GPU memory
def find_large_tensors(min_size_mb=1):
    """List all tensors on GPU larger than min_size_mb."""
    import gc
    gc.collect()
    torch.cuda.empty_cache()

    tensors = []
    for obj in gc.get_objects():
        try:
            if torch.is_tensor(obj) and obj.is_cuda:
                size_mb = obj.element_size() * obj.nelement() / 1e6
                if size_mb >= min_size_mb:
                    tensors.append((size_mb, obj.shape, obj.dtype, obj.device))
        except Exception:
            pass

    tensors.sort(reverse=True)
    for size, shape, dtype, device in tensors[:20]:
        print(f"  {size:8.1f} MB | {str(shape):30s} | {dtype} | {device}")
```

```bash
# Memory reduction strategies (apply in order)
python -c "
strategies = [
    '1. Reduce batch_size (halve it)',
    '2. Use torch.cuda.amp.autocast() for mixed precision (FP16)',
    '3. Use gradient accumulation (effective_batch = batch * accum_steps)',
    '4. Enable gradient checkpointing (trades compute for memory)',
    '5. Use torch.utils.checkpoint.checkpoint() for specific layers',
    '6. Move to CPU for evaluation: model.eval(); torch.no_grad()',
    '7. Clear cache between steps: torch.cuda.empty_cache()',
    '8. Use DataLoader with pin_memory=True and num_workers>0',
    '9. Reduce model size (fewer layers, smaller hidden dimensions)',
    '10. Use DeepSpeed ZeRO or FSDP for multi-GPU memory sharing',
]
for s in strategies:
    print(s)
"
```

## Gradient Debugging Section

```python
# Check gradient flow through the model
def check_gradient_flow(model):
    """Verify gradients are flowing to all parameters."""
    for name, param in model.named_parameters():
        if param.requires_grad:
            if param.grad is None:
                print(f"  NO GRAD:  {name}")
            elif param.grad.abs().max() == 0:
                print(f"  ZERO GRAD: {name} (vanishing gradient)")
            elif torch.isnan(param.grad).any():
                print(f"  NaN GRAD:  {name} (exploding gradient)")
            elif torch.isinf(param.grad).any():
                print(f"  Inf GRAD:  {name} (exploding gradient)")
            else:
                print(f"  OK:        {name} | grad norm: {param.grad.norm():.6f}")
```

```python
# Detect NaN/Inf in forward pass
torch.autograd.set_detect_anomaly(True)  # Enable anomaly detection (slow, debug only)

# Check for NaN in loss
def safe_backward(loss):
    """Check loss before backward pass."""
    if torch.isnan(loss):
        raise ValueError(f"NaN loss detected: {loss.item()}")
    if torch.isinf(loss):
        raise ValueError(f"Inf loss detected: {loss.item()}")
    loss.backward()
```

## Hard Rules

- **ALWAYS** test with `batch_size=2` first before increasing. This catches shape errors with minimal resource usage. Use 2 (not 1) to expose batch dimension bugs.
- **NEVER** use `.item()` inside a training loop on a tensor that is part of the computation graph. Detach first: `loss.detach().item()`.
- **NEVER** store tensors in Python lists across training steps without detaching. This prevents garbage collection and causes memory leaks: `losses.append(loss.detach().cpu())`.
- **NEVER** use `torch.autograd.set_detect_anomaly(True)` in production. It is for debugging only and severely impacts performance.
- **NEVER** silence shape errors by reshaping without understanding the semantics. A wrong reshape produces silent bugs in model accuracy.
- **ALWAYS** set `model.eval()` and use `with torch.no_grad():` during validation and inference.
- **ALWAYS** verify device consistency before matrix operations: `assert x.device == weight.device`.
- **ALWAYS** check `requires_grad` state when gradients are missing: `print([(n, p.requires_grad) for n, p in model.named_parameters()])`.

## Stop Conditions

- The error requires CUDA driver or hardware changes that cannot be resolved in software (driver version mismatch, GPU hardware fault). Escalate with the CUDA version and GPU model.
- The error is a numerical instability (NaN/Inf) that persists after learning rate reduction, gradient clipping, and batch normalization. Document the training configuration and escalate.
- Two fix attempts have failed for the same runtime error. Provide the root cause analysis, shape traces, and both attempted approaches to the user.

## Output Format

```
[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>
  Shapes: <input_shape> -> <expected_shape> (was <actual_shape>)

[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

Build Status: PASS | python train.py --batch-size 2 --epochs 1 | no shape errors | no device errors
```
