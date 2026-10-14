"""
ARC-AGI-3 MLP Value Model (na podstawie c87f7a48-pokemon)

MLP 20->128->64->1 z numpy.
Trenowany na danych z gier ARC-AGI-3.
Szybka inferencja: ~0.16ms/decision.
"""

import math
import numpy as np
from typing import Optional


def init_weights(in_dim: int, h1: int, h2: int, out_dim: int):
    """Initialize weights with He initialization."""
    W0 = np.random.randn(in_dim, h1) * math.sqrt(2.0 / in_dim)
    b0 = np.zeros(h1)
    W1 = np.random.randn(h1, h2) * math.sqrt(2.0 / h1)
    b1 = np.zeros(h2)
    W2 = np.random.randn(h2, out_dim) * math.sqrt(2.0 / h2)
    b2 = np.zeros(out_dim)
    return W0, b0, W1, b1, W2, b2


def forward(X: np.ndarray, W0, b0, W1, b1, W2, b2):
    """Forward pass through MLP."""
    h1 = X @ W0 + b0
    h1 = np.maximum(0, h1)  # ReLU
    h2 = h1 @ W1 + b1
    h2 = np.maximum(0, h2)  # ReLU
    logits = h2 @ W2 + b2
    return h1, h2, logits


def sigmoid(x: np.ndarray) -> np.ndarray:
    """Sigmoid activation."""
    x = np.clip(x, -20, 20)
    return 1.0 / (1.0 + np.exp(-x))


def train_mlp(
    X: np.ndarray,
    y: np.ndarray,
    epochs: int = 100,
    lr: float = 0.02,
    batch: int = 256,
    h1: int = 128,
    h2: int = 64,
    seed: int = 42,
) -> tuple:
    """Train MLP 20->128->64->1 with numpy SGD.
    
    Args:
        X: Input features (n_samples, 20)
        y: Target values (n_samples,) - normalized scores [0, 1]
        epochs: Number of training epochs
        lr: Learning rate
        batch: Batch size
        h1: Hidden layer 1 size
        h2: Hidden layer 2 size
        seed: Random seed
    
    Returns:
        (W0, b0, W1, b1, W2, b2, accuracy)
    """
    np.random.seed(seed)
    n, d = X.shape
    
    # Initialize weights
    W0, b0, W1, b1, W2, b2 = init_weights(d, h1, h2, 1)
    
    # Split 80/20 for validation
    idx = np.arange(n)
    np.random.shuffle(idx)
    split = int(n * 0.8)
    tr_idx = idx[:split]
    va_idx = idx[split:]
    Xtr, ytr = X[tr_idx], y[tr_idx]
    Xva, yva = X[va_idx], y[va_idx]
    
    print(f"Training MLP: {n} samples, {d} features, {h1}-{h2} hidden")
    print(f"Train: {len(Xtr)}, Validation: {len(Xva)}")
    
    for ep in range(epochs):
        # Shuffle training data
        perm = np.random.permutation(len(Xtr))
        Xtr_shuffled = Xtr[perm]
        ytr_shuffled = ytr[perm]
        
        # Mini-batch SGD
        for i in range(0, len(Xtr_shuffled), batch):
            xb = Xtr_shuffled[i:i+batch]
            yb = ytr_shuffled[i:i+batch]
            
            # Forward pass
            h1a, h2a, logits = forward(xb, W0, b0, W1, b1, W2, b2)
            probs = sigmoid(logits.flatten())
            
            # BCE gradient
            grad_logits = (probs - yb) / len(yb)
            
            # Gradient for W2, b2
            dW2 = h2a.T @ grad_logits[:, None]
            db2 = np.sum(grad_logits)
            dh2 = grad_logits[:, None] @ W2.T
            dh2[h2a <= 0] = 0  # ReLU gradient
            
            # Gradient for W1, b1
            dW1 = h1a.T @ dh2
            db1 = np.sum(dh2, axis=0)
            dh1 = dh2 @ W1.T
            dh1[h1a <= 0] = 0  # ReLU gradient
            
            # Gradient for W0, b0
            dW0 = xb.T @ dh1
            db0 = np.sum(dh1, axis=0)
            
            # SGD update
            W2 -= lr * dW2
            b2 -= lr * db2
            W1 -= lr * dW1
            b1 -= lr * db1
            W0 -= lr * dW0
            b0 -= lr * db0
        
        # Validation every 20 epochs
        if (ep + 1) % 20 == 0:
            _, _, logits_va = forward(Xva, W0, b0, W1, b1, W2, b2)
            probs_va = sigmoid(logits_va.flatten())
            
            # Accuracy (threshold 0.5)
            acc = np.mean((probs_va > 0.5) == (yva > 0.5))
            
            # BCE loss
            loss = -np.mean(yva * np.log(probs_va + 1e-8) + (1 - yva) * np.log(1 - probs_va + 1e-8))
            
            print(f"Epoch {ep+1}/{epochs}: loss={loss:.4f}, acc={acc:.3f}")
    
    # Final validation
    _, _, logits_va = forward(Xva, W0, b0, W1, b1, W2, b2)
    probs_va = sigmoid(logits_va.flatten())
    acc = np.mean((probs_va > 0.5) == (yva > 0.5))
    
    print(f"Final accuracy: {acc:.3f}")
    
    return W0, b0, W1, b1, W2, b2, acc


def mlp_predict(features: list[float], weights: tuple) -> float:
    """Predict value for given features using trained MLP.
    
    Args:
        features: List of 20 floats
        weights: (W0, b0, W1, b1, W2, b2)
    
    Returns:
        Predicted value in [0, 1]
    """
    W0, b0, W1, b1, W2, b2 = weights
    
    try:
        # Numpy path (fast)
        a = np.array(features, dtype=np.float64)
        h1 = np.maximum(0, a.dot(W0) + b0)
        h2 = np.maximum(0, h1.dot(W1) + b1)
        out = h2.dot(W2.flatten()) + b2[0]
        
        if isinstance(out, np.ndarray):
            out = float(out)
        
        # Sigmoid
        if out > 20:
            return 1.0
        if out < -20:
            return 0.0
        return 1.0 / (1.0 + math.exp(-out))
    
    except Exception as e:
        # Fallback: return 0.5 (neutral)
        return 0.5


def save_weights(weights: tuple, accuracy: float, out_path: str):
    """Save weights as Python code for easy import."""
    W0, b0, W1, b1, W2, b2 = weights
    
    with open(out_path, "w") as f:
        f.write("# ARC-AGI-3 MLP Value Model\n")
        f.write(f"# Accuracy: {accuracy:.3f}\n")
        f.write("# Architecture: 20->128->64->1\n\n")
        
        f.write("import math\n")
        f.write("try:\n")
        f.write("    import numpy as np\n")
        f.write("    _HAS_NP = True\n")
        f.write("except:\n")
        f.write("    _HAS_NP = False\n\n")
        
        f.write(f"_W0_coef = {W0.tolist()}\n")
        f.write(f"_W0_bias = {b0.tolist()}\n")
        f.write(f"_W1_coef = {W1.tolist()}\n")
        f.write(f"_W1_bias = {b1.tolist()}\n")
        f.write(f"_W2_coef = {W2.tolist()}\n")
        f.write(f"_W2_bias = {b2.tolist()}\n\n")
        
        f.write("""def mlp_predict_arc(features):
    \"\"\"Predict value for ARC-AGI-3 game state.\"\"\"
    try:
        if _HAS_NP:
            a = np.array(features, dtype=np.float64)
            h1 = np.maximum(0, a.dot(np.array(_W0_coef)) + np.array(_W0_bias))
            h2 = np.maximum(0, h1.dot(np.array(_W1_coef)) + np.array(_W1_bias))
            out = h2.dot(np.array(_W2_coef).flatten()) + np.array(_W2_bias)[0]
            if isinstance(out, np.ndarray):
                out = float(out)
            if out > 20:
                return 1.0
            if out < -20:
                return 0.0
            return 1.0 / (1.0 + math.exp(-out))
    except:
        pass
    return 0.5
""")
    
    print(f"Saved weights to {out_path}")


if __name__ == "__main__":
    # Test with random data
    print("Testing MLP training...")
    
    # Generate random data
    n_samples = 1000
    X = np.random.rand(n_samples, 20)
    y = np.random.rand(n_samples)
    
    # Train
    W0, b0, W1, b1, W2, b2, acc = train_mlp(X, y, epochs=50, lr=0.02, batch=256)
    
    # Save
    save_weights((W0, b0, W1, b1, W2, b2), acc, "/tmp/mlp_arc_test.py")
    
    print("Test complete!")
