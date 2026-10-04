# Real-ESRGAN ONNX Tiling & Seam Blending Mathematics

This document explains the mathematical foundations of the high-speed, zero-seam tiling algorithm implemented in the FreeUpscaler ONNX engine.

---

## 1. Why Tiling is Essential

Running convolutional super-resolution models (like Real-ESRGAN) on full high-resolution images (e.g., $1920 \times 1080$ or $4000 \times 3000$) requires massive amounts of VRAM/RAM:
- Activation memory scales quadratically ($O(W \times H)$) with image area.
- An un-tiled $4K$ inference pass easily requires **8–16 GB of RAM**, causing instant OOM crashes on standard cloud VPS instances (which typically have 2–4 GB RAM).

**The Solution:** Divide the input image into small fixed-size tiles ($128 \times 128$), run inference on each tile independently, and reconstruct the output ($512 \times 512$ per tile).

---

## 2. The Boundary Artifact Problem

If tiles are cut and pasted directly without overlap:
- Convolutional padding (reflection/zero padding) at the edges of each tile causes noticeable boundary artifacts and harsh grid lines.
- Color shifts across neighboring receptive fields make tile boundaries plainly visible.

To achieve **flawless, invisible tile transitions**, two techniques must be combined:
1. **Overlapping Tile Coordinate Generation (16px overlap)**
2. **2D Smooth Triangular / Cosine Ramp Weight Blending**

---

## 3. Mathematical Coordinate Generation

Given an image dimension $L$ (width or height):
- Tile size: $T = 128$
- Tile step: $S = 112$
- Overlap: $O = T - S = 16\text{ px}$

For an arbitrary length $L$:
1. If $L \le 128$, the tile coordinate is simply $[0]$.
2. Otherwise, start at index $r = 0$, step forward by $112$:
   $$r_{k+1} = r_k + 112 \quad \text{while } r + 128 < L$$
3. Append the final boundary tile index:
   $$r_{\text{last}} = L - 128$$
4. Remove duplicates and sort.

```python
def get_tile_indices(length: int, tile_size: int = 128, step: int = 112) -> list[int]:
    if length <= tile_size:
        return [0]
    indices = []
    r = 0
    while r + tile_size < length:
        indices.append(r)
        r += step
    indices.append(length - tile_size)
    return sorted(list(set(indices)))
```

---

## 4. 2D Smooth Ramp Blending Matrix

When a $128 \times 128$ tile is passed through a $4\times$ Real-ESRGAN model, it yields a $512 \times 512$ tile.
The 16px input overlap becomes a **64px output overlap** ($16 \times 4$).

To blend overlapping tiles smoothly without brightness spikes or visible seams, we construct a 1D ramp function $w(t)$ of length $512$:

$$
w(t) = \min\left( \frac{t}{64}, \, \frac{511 - t}{64}, \, 1.0 \right) \quad \text{for } t \in [0, 511]
$$

Then compute the 2D separable outer product:
$$
W(x, y) = w(x) \times w(y)
$$

This creates a smooth fall-off window that ramps from 0 at the extreme edges up to 1.0 in the interior.

### Canvas Accumulation Formula:
We maintain two accumulator canvases for the entire output:
1. `output_canvas`: shape $(4H, 4W, 3)$, dtype `float32` (initialized to 0)
2. `weight_canvas`: shape $(4H, 4W)$, dtype `float32` (initialized to 0)

For each processed tile $P_{i,j}$ placed at output coordinates $(4y_i : 4y_i + 512, 4x_j : 4x_j + 512)$:
$$
\text{output\_canvas}[Y, X] \mathrel{+}= P_{i,j} \odot W
$$
$$
\text{weight\_canvas}[Y, X] \mathrel{+}= W
$$

### Final Normalization:
After all tiles have accumulated:
$$
\text{FinalImage}[Y, X] = \frac{\text{output\_canvas}[Y, X]}{\text{weight\_canvas}[Y, X]}
$$
Followed by clipping to $[0, 255]$ and casting to `uint8`.

**Result:** Zero visible grid lines, uniform luminance, and zero boundary edge distortions.

---

## 5. Alpha Channel (Transparency) Preservation

Real-ESRGAN models operate strictly on 3-channel RGB ($3 \times H \times W$). If an RGBA image is passed directly, alpha information is lost or corrupted.

**Algorithm:**
1. Check if input image mode is `'RGBA'`.
2. If RGBA:
   - Split into `RGB = img.convert('RGB')` and `A = img.split()[-1]`.
   - Upscale `RGB` via the ONNX tiled engine.
   - Upscale the Alpha mask `A` using high-fidelity **Lanczos resampling** directly to matching dimensions $(4W, 4H)$ or $(2W, 2H)$.
   - Recombine: `final_rgba = Image.merge('RGBA', (*upscaled_rgb.split(), upscaled_alpha))`.
3. If RGB:
   - Process directly and output clean RGB.
