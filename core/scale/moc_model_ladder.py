"""HENLA-MoC-SCALE 5: Model Size Ladder.

Defines the configuration logic for the Parameter Golf, providing the exact
hyperparameters for the various federated scales (Micro, Tiny, Small, etc.).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict


@dataclass
class ModelConfig:
    """Standard Transformer configuration for an individual cognitive area."""
    n_layer: int
    n_head: int
    n_embd: int
    vocab_size: int = 50257
    block_size: int = 1024
    
    tie_weights: bool = True
    
    @property
    def parameter_count(self) -> int:
        """Rough estimate of the parameter count for this configuration."""
        # Embedding: vocab_size * n_embd + block_size * n_embd
        embedding = (self.vocab_size * self.n_embd) + (self.block_size * self.n_embd)
        
        # Self-Attention per layer: 3x weights for QKV, 1x for output projection
        attention = 4 * (self.n_embd ** 2)
        
        # FFN per layer: up-proj (4x), down-proj (4x) 
        ffn = 8 * (self.n_embd ** 2)
        
        # Layer Norms
        ln = 4 * self.n_embd
        
        layer = attention + ffn + ln
        
        # LM Head: un-embedding
        lm_head = 0 if self.tie_weights else (self.n_embd * self.vocab_size)
        
        total = embedding + (self.n_layer * layer) + lm_head
        return total


class MoCSizeLadder:
    """Manages the network dimensions for the federated cognitive scales."""
    
    # Pre-calculated configurations
    CONFIGS = {
        # ~10M parameters per area (80M total)
        "micro": ModelConfig(n_layer=4, n_head=2, n_embd=128),
        
        # ~25M parameters per area (200M total)
        "tiny": ModelConfig(n_layer=12, n_head=4, n_embd=256),
        
        # ~125M parameters per area (1B total)
        "small": ModelConfig(n_layer=12, n_head=12, n_embd=768),
        
        # ~350M parameters per area (2.8B total)
        "base": ModelConfig(n_layer=24, n_head=16, n_embd=1024),
    }

    @classmethod
    def get_moc_config(cls, scale: str) -> Dict[str, Any]:
        """Returns the configuration for a MoC federation at the given scale."""
        scale = scale.lower()
        if scale not in cls.CONFIGS:
            raise ValueError(f"Unknown scale: {scale}. Choose from {list(cls.CONFIGS.keys())}")
            
        area_config = cls.CONFIGS[scale]
        area_params = area_config.parameter_count
        
        return {
            "scale_name": scale,
            "areas_count": 8,
            "area_config": area_config.__dict__,
            "params_per_area_approx": f"{area_params / 1e6:.1f}M",
            "total_federation_params_approx": f"{(area_params * 8) / 1e6:.1f}M"
        }

    @classmethod
    def get_monolithic_baseline_config(cls, scale: str) -> ModelConfig:
        """Returns a single transformer config roughly matching the TOTAL MoC parameters.
        This is crucial for the SCALE-6 Parameter Golf (MoC vs Monolith).
        """
        scale = scale.lower()
        
        # Monolithic baselines designed to have ~8x the parameters of an individual area
        baselines = {
            # Target ~58M total (matches Micro MoC)
            "micro": ModelConfig(n_layer=20, n_head=6, n_embd=384), 
            
            # Target ~180M total (matches Tiny MoC)
            "tiny": ModelConfig(n_layer=20, n_head=12, n_embd=768),
            
            # Target ~1B total (matches Small MoC)
            "small": ModelConfig(n_layer=24, n_head=16, n_embd=1536),
            
            # Target ~2.8B total (matches Base MoC)
            "base": ModelConfig(n_layer=32, n_head=32, n_embd=2560),
        }
        
        return baselines.get(scale)
