"""
Minimal Standalone Real-ESRGAN ONNX Tiler with Seam Blending.
Can be run directly on any image:
    python onnx_tiler_minimal.py input.jpg output.png --scale 4 --model path/to/model.onnx
"""

import sys
import argparse
from pathlib import Path
import numpy as np
from PIL import Image
import onnxruntime as ort

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

def create_ramp_weights() -> np.ndarray:
    ramp = np.ones(512, dtype=np.float32)
    for t in range(512):
        r = min(t, 64) / 64.0
        n = min(511 - t, 64) / 64.0
        ramp[t] = min(r, n, 1.0)
    return np.outer(ramp, ramp).astype(np.float32)

def upscale_image(
    image_path: Path,
    model_path: Path,
    output_path: Path,
    scale: int = 4
) -> None:
    print(f"Loading model: {model_path}")
    sess = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    inp_name = sess.get_inputs()[0].name
    out_name = sess.get_outputs()[0].name
    
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    img_np = np.array(img, dtype=np.float32) / 255.0
    
    tile_weights = create_ramp_weights()
    x_indices = get_tile_indices(w)
    y_indices = get_tile_indices(h)
    
    target_w, target_h = w * 4, h * 4
    output_canvas = np.zeros((target_h, target_w, 3), dtype=np.float32)
    weight_canvas = np.zeros((target_h, target_w), dtype=np.float32)
    
    total_tiles = len(y_indices) * len(x_indices)
    print(f"Processing image {w}x{h} ({total_tiles} tiles of 128x128)...")
    
    count = 0
    for y in y_indices:
        for x in x_indices:
            count += 1
            # Extract 128x128 tile (pad if image is smaller than 128)
            tile = np.zeros((128, 128, 3), dtype=np.float32)
            actual_crop = img_np[y:y+128, x:x+128]
            th, tw, _ = actual_crop.shape
            tile[:th, :tw] = actual_crop
            
            # (1, 3, 128, 128)
            tensor_in = np.transpose(tile, (2, 0, 1))[np.newaxis, ...]
            tensor_out = sess.run([out_name], {inp_name: tensor_in})[0]
            
            # (512, 512, 3)
            out_tile = np.transpose(tensor_out[0], (1, 2, 0))
            out_tile = np.clip(out_tile, 0.0, 1.0)
            
            # Accumulate on canvas with 2D ramp weights
            out_y, out_x = y * 4, x * 4
            accum_h = min(512, target_h - out_y)
            accum_w = min(512, target_w - out_x)
            
            sub_weight = tile_weights[:accum_h, :accum_w]
            for c in range(3):
                output_canvas[out_y:out_y+accum_h, out_x:out_x+accum_w, c] += out_tile[:accum_h, :accum_w, c] * sub_weight
            weight_canvas[out_y:out_y+accum_h, out_x:out_x+accum_w] += sub_weight
            
            if count % 10 == 0 or count == total_tiles:
                print(f"Tile {count}/{total_tiles} ({count*100//total_tiles}%)")
                
    # Normalize by accumulated weights
    weight_canvas = np.maximum(weight_canvas, 1e-4)
    normalized = output_canvas / weight_canvas[..., np.newaxis]
    res_np = np.clip(normalized * 255.0, 0, 255).astype(np.uint8)
    res_img = Image.fromarray(res_np)
    
    # If 2x scale requested, downsample using Lanczos
    if scale == 2:
        res_img = res_img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
        
    res_img.save(output_path)
    print(f"Saved upscaled image to {output_path} ({res_img.size[0]}x{res_img.size[1]})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-ESRGAN Minimal Tiler")
    parser.add_argument("input", type=Path, help="Input image path")
    parser.add_argument("output", type=Path, help="Output image path")
    parser.add_argument("--model", type=Path, required=True, help="Path to RealESRGAN ONNX model")
    parser.add_argument("--scale", type=int, default=4, choices=[2, 4], help="Scale factor (2 or 4)")
    args = parser.parse_args()
    
    upscale_image(args.input, args.model, args.output, scale=args.scale)
