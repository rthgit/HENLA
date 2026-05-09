"""HENLA-MoC-SCALE 7: Area Pretraining Script.

Trains a specific cognitive area LLM using the Shared Experience Stream.
In production, this script would run in parallel across 8 different nodes/processes.
"""

import os
import torch
import argparse
from torch.optim import AdamW
from core.scale.moc_model_ladder import MoCSizeLadder
from core.scale.moc_transformer import MoCAreaTransformer
from core.scale.fineweb_streamer import FineWebExperienceStreamer


def train_area(area_name: str, scale: str, max_steps: int = 100):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"--- Training HENLA-MoC Area: {area_name.upper()} [{scale.upper()}] on {device} ---")
    
    # 1. Init Model
    config_data = MoCSizeLadder.get_moc_config(scale)
    model_config = MoCSizeLadder.CONFIGS[scale]
    model = MoCAreaTransformer(model_config).to(device)
    print(f"Model instantiated. Parameters: {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M")
    
    optimizer = AdamW(model.parameters(), lr=3e-4, weight_decay=0.1)
    
    # 2. Init Streamer
    streamer = FineWebExperienceStreamer()
    
    # 3. Dummy Training Loop (Simulating optimization on specific area targets)
    model.train()
    step = 0
    
    for experience in streamer.stream_experiences(limit=max_steps):
        # In a real scenario, we would tokenize the raw text + the area-specific target
        # For this setup, we simulate the forward/backward pass with random tokens
        
        # Simulating sequence: <text> [SEP] <structured_target>
        dummy_seq_len = 128
        idx = torch.randint(0, model_config.vocab_size, (1, dummy_seq_len)).to(device)
        targets = idx.clone() # Next token prediction
        
        optimizer.zero_grad()
        logits, loss = model(idx, targets=targets)
        loss.backward()
        optimizer.step()
        
        if step % 10 == 0:
            print(f"Step {step} | Loss: {loss.item():.4f} | Area: {area_name}")
            
        step += 1
        
    print(f"Training for {area_name} completed.")
    
    # Save checkpoint
    os.makedirs(f".checkpoints/{area_name}", exist_ok=True)
    torch.save(model.state_dict(), f".checkpoints/{area_name}/model_{scale}.pt")
    print(f"Checkpoint saved to .checkpoints/{area_name}/model_{scale}.pt")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", type=str, default="semantic", 
                        choices=["episodic", "semantic", "procedural", "predictive", 
                                 "analogical", "linguistic", "safety", "metacognitive"])
    parser.add_argument("--scale", type=str, default="tiny", choices=["micro", "tiny", "small", "base"])
    parser.add_argument("--steps", type=int, default=50)
    args = parser.parse_args()
    
    train_area(args.area, args.scale, args.steps)
