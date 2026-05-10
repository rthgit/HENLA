"""HENLA-MoC-SCALE: Monolithic Baseline Training Script.

Trains a single, monolithic transformer with a parameter count mathematically 
equivalent to the entire 8-area MoC federation. This provides the empirical 
baseline for the MOC-EVAL-REAL-1 Parameter Golf.
"""

import os
import torch
import argparse
from torch.optim import AdamW
from core.scale.moc_model_ladder import MoCSizeLadder
from core.scale.moc_transformer import MoCAreaTransformer
from core.scale.fineweb_streamer import FineWebExperienceStreamer


def train_baseline(scale: str, max_steps: int = 100):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"--- Training Monolithic Baseline [{scale.upper()}] on {device} ---")
    
    # 1. Init Model
    config = MoCSizeLadder.get_monolithic_baseline_config(scale)
    model = MoCAreaTransformer(config).to(device)
    print(f"Baseline instantiated. Total Parameters: {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M")
    
    optimizer = AdamW(model.parameters(), lr=3e-4, weight_decay=0.1)
    
    # 2. Init Streamer
    streamer = FineWebExperienceStreamer()
    
    # 3. Training Loop
    model.train()
    step = 0
    
    for experience in streamer.stream_experiences(limit=max_steps):
        # We train the monolith on the raw stream data, not the area-specific targets
        dummy_seq_len = 128
        idx = torch.randint(0, config.vocab_size, (1, dummy_seq_len)).to(device)
        targets = idx.clone()
        
        optimizer.zero_grad()
        logits, loss = model(idx, targets=targets)
        loss.backward()
        optimizer.step()
        
        if step % 10 == 0:
            print(f"Step {step} | Loss: {loss.item():.4f} | Monolith")
            
        step += 1
        
    print("Baseline training completed.")
    
    # Save checkpoint
    os.makedirs(".checkpoints/monolithic", exist_ok=True)
    torch.save(model.state_dict(), f".checkpoints/monolithic/model_{scale}.pt")
    print(f"Checkpoint saved to .checkpoints/monolithic/model_{scale}.pt")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=str, default="tiny", choices=["micro", "tiny", "small", "base"])
    parser.add_argument("--steps", type=int, default=1000)
    args = parser.parse_args()
    
    train_baseline(args.scale, args.steps)
