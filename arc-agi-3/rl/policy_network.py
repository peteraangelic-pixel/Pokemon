"""Simple MLP policy network for ARC-AGI.
Inspired by Pokemon TCG's Transformer+Pointer architecture.

This is a minimal viable version - can be upgraded to Transformer later.
"""
import numpy as np
from typing import List, Dict, Any, Tuple


class MLPPolicy:
    """Simple MLP policy: state_features → action probabilities."""
    
    def __init__(self, input_dim: int, hidden_dim: int = 128, num_actions: int = 8):
        """Initialize policy.
        
        Args:
            input_dim: Dimension of state features
            hidden_dim: Hidden layer size
            num_actions: Number of possible actions
        """
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_actions = num_actions
        
        # Initialize weights (Xavier initialization)
        self.W1 = np.random.randn(input_dim, hidden_dim) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.randn(hidden_dim, num_actions) * np.sqrt(2.0 / hidden_dim)
        self.b2 = np.zeros(num_actions)
    
    def forward(self, state_features: np.ndarray) -> np.ndarray:
        """Forward pass: state → action logits.
        
        Args:
            state_features: [input_dim] feature vector
        
        Returns:
            action_logits: [num_actions] logits
        """
        # Hidden layer with ReLU
        hidden = np.maximum(0, state_features @ self.W1 + self.b1)
        
        # Output layer
        logits = hidden @ self.W2 + self.b2
        
        return logits
    
    def get_action_probs(self, state_features: np.ndarray, temperature: float = 1.0) -> np.ndarray:
        """Get action probabilities.
        
        Args:
            state_features: [input_dim] feature vector
            temperature: Sampling temperature
        
        Returns:
            action_probs: [num_actions] probabilities
        """
        logits = self.forward(state_features)
        
        # Softmax with temperature
        logits = logits / temperature
        exp_logits = np.exp(logits - np.max(logits))  # Numerical stability
        probs = exp_logits / np.sum(exp_logits)
        
        return probs
    
    def sample_action(self, state_features: np.ndarray, temperature: float = 1.0) -> int:
        """Sample action from policy.
        
        Args:
            state_features: [input_dim] feature vector
            temperature: Sampling temperature
        
        Returns:
            action: Sampled action index
        """
        probs = self.get_action_probs(state_features, temperature)
        action = np.random.choice(self.num_actions, p=probs)
        return action
    
    def save(self, path: str) -> None:
        """Save policy weights."""
        np.savez(
            path,
            W1=self.W1, b1=self.b1,
            W2=self.W2, b2=self.b2,
            input_dim=self.input_dim,
            hidden_dim=self.hidden_dim,
            num_actions=self.num_actions
        )
    
    def load(self, path: str) -> None:
        """Load policy weights."""
        data = np.load(path)
        self.W1 = data['W1']
        self.b1 = data['b1']
        self.W2 = data['W2']
        self.b2 = data['b2']
        self.input_dim = int(data['input_dim'])
        self.hidden_dim = int(data['hidden_dim'])
        self.num_actions = int(data['num_actions'])


def extract_features(game_state: Dict[str, Any]) -> np.ndarray:
    """Extract feature vector from game state.
    
    Features (example - can be expanded):
    - Grid values (flattened)
    - Player position (x, y)
    - Score
    - Level
    - Lives
    - Time remaining
    
    Args:
        game_state: Game observation dict
    
    Returns:
        features: [input_dim] feature vector
    """
    features = []
    
    # Grid features (flatten 2D grid)
    if 'grid' in game_state:
        grid = np.array(game_state['grid'])
        features.extend(grid.flatten())
    
    # Player position
    if 'player' in game_state:
        features.append(game_state['player'].get('x', 0))
        features.append(game_state['player'].get('y', 0))
    
    # Game state
    features.append(game_state.get('score', 0))
    features.append(game_state.get('level', 1))
    features.append(game_state.get('lives', 3))
    features.append(game_state.get('time', 0))
    
    return np.array(features, dtype=np.float32)


class BCTrainer:
    """Behavior Cloning trainer."""
    
    def __init__(self, policy: MLPPolicy, learning_rate: float = 0.001):
        """Initialize trainer.
        
        Args:
            policy: Policy network to train
            learning_rate: Learning rate for SGD
        """
        self.policy = policy
        self.lr = learning_rate
        
        # Gradient storage
        self.dW1 = None
        self.db1 = None
        self.dW2 = None
        self.db2 = None
    
    def compute_loss(
        self,
        states: np.ndarray,
        actions: np.ndarray
    ) -> Tuple[float, np.ndarray]:
        """Compute cross-entropy loss and gradients.
        
        Args:
            states: [batch, input_dim] state features
            actions: [batch] action indices
        
        Returns:
            loss: Cross-entropy loss
            grads: Gradient tuple (dW1, db1, dW2, db2)
        """
        batch_size = len(states)
        
        # Forward pass
        hidden = np.maximum(0, states @ self.policy.W1 + self.policy.b1)
        logits = hidden @ self.policy.W2 + self.policy.b2
        
        # Softmax
        exp_logits = np.exp(logits - np.max(logits, axis=1, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)
        
        # Cross-entropy loss
        log_probs = -np.log(probs[np.arange(batch_size), actions] + 1e-8)
        loss = np.mean(log_probs)
        
        # Backward pass
        dlogits = probs
        dlogits[np.arange(batch_size), actions] -= 1
        dlogits /= batch_size
        
        # Gradients
        dW2 = hidden.T @ dlogits
        db2 = np.sum(dlogits, axis=0)
        
        dhidden = dlogits @ self.policy.W2.T
        dhidden[hidden <= 0] = 0  # ReLU backward
        
        dW1 = states.T @ dhidden
        db1 = np.sum(dhidden, axis=0)
        
        return loss, (dW1, db1, dW2, db2)
    
    def update(self, grads: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]) -> None:
        """Update policy weights with SGD.
        
        Args:
            grads: Gradient tuple (dW1, db1, dW2, db2)
        """
        dW1, db1, dW2, db2 = grads
        
        self.policy.W1 -= self.lr * dW1
        self.policy.b1 -= self.lr * db1
        self.policy.W2 -= self.lr * dW2
        self.policy.b2 -= self.lr * db2
    
    def train_step(self, states: np.ndarray, actions: np.ndarray) -> float:
        """Single training step.
        
        Args:
            states: [batch, input_dim] state features
            actions: [batch] action indices
        
        Returns:
            loss: Cross-entropy loss
        """
        loss, grads = self.compute_loss(states, actions)
        self.update(grads)
        return loss


if __name__ == "__main__":
    # Quick test
    policy = MLPPolicy(input_dim=100, hidden_dim=64, num_actions=8)
    
    # Test forward pass
    state = np.random.randn(100)
    logits = policy.forward(state)
    print(f"Logits shape: {logits.shape}")
    print(f"Logits: {logits}")
    
    # Test sampling
    action = policy.sample_action(state, temperature=1.0)
    print(f"Sampled action: {action}")
    
    # Test save/load
    policy.save("/tmp/test_policy.npz")
    policy2 = MLPPolicy(input_dim=100, hidden_dim=64, num_actions=8)
    policy2.load("/tmp/test_policy.npz")
    print("Save/load test passed")
