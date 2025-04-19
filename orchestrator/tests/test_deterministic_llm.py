"""
Demonstrates deterministic LLM testing using seeded models and snapshots.
"""
import os
import pytest
from pathlib import Path
import json

# Create a mock for the LLM service to avoid actual API calls during testing
class MockLLMService:
    def __init__(self, seed=None, snapshot_mode=False):
        self.seed = seed
        self.snapshot_mode = snapshot_mode
        self.snapshot_dir = Path("tests/snapshots/llm_responses")
        
        # Create snapshot directory if it doesn't exist and snapshot mode is enabled
        if self.snapshot_mode and not self.snapshot_dir.exists():
            self.snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    def process(self, input_data):
        """
        Mock LLM processing with deterministic outputs based on seed.
        
        In real testing, this would use the actual LLMService with a seed.
        """
        if isinstance(input_data, str):
            prompt = input_data
        elif isinstance(input_data, dict):
            prompt = input_data.get("user", "") 
            if "system" in input_data:
                prompt = f"{input_data['system']}\n{prompt}"
        else:
            # Assume it's a list of message objects in this mock
            prompt = "\n".join([msg.content for msg in input_data])
        
        # Use a simple hash of the prompt + seed for deterministic output
        if self.seed is not None:
            # Deterministic output based on seed
            import hashlib
            prompt_hash = hashlib.md5(f"{prompt}:{self.seed}".encode()).hexdigest()
            return {
                "content": f"Deterministic response for {prompt_hash[:8]}",
                "model": "mock-model",
                "metadata": {"seed": self.seed}
            }
        else:
            # Non-deterministic output simulation
            import random
            rand_suffix = random.randint(1000, 9999)
            return {
                "content": f"Random response {rand_suffix}",
                "model": "mock-model",
                "metadata": {}
            }


# Test cases demonstrating deterministic testing

def test_seeded_model_determinism():
    """Test that seeded models produce consistent outputs."""
    # Create service with fixed seed
    llm_service = MockLLMService(seed=42)
    
    # First call
    result1 = llm_service.process("Tell me a joke")
    
    # Second call with same input
    result2 = llm_service.process("Tell me a joke")
    
    # The outputs should be identical with the same seed
    assert result1["content"] == result2["content"], "Seeded outputs should be deterministic"
    
    # Different input should produce different but deterministic output
    result3 = llm_service.process("Tell me a story")
    assert result1["content"] != result3["content"], "Different inputs should produce different outputs"
    
    # Same different input should produce same output
    result4 = llm_service.process("Tell me a story")
    assert result3["content"] == result4["content"], "Same input should produce same output with seed"


def test_different_seeds_produce_different_outputs():
    """Test that different seeds produce different but consistent outputs."""
    # First service with seed 42
    llm_service1 = MockLLMService(seed=42)
    
    # Second service with seed 43
    llm_service2 = MockLLMService(seed=43)
    
    # Same input, different seeds
    result1 = llm_service1.process("Tell me a joke")
    result2 = llm_service2.process("Tell me a joke")
    
    # The outputs should be different with different seeds
    assert result1["content"] != result2["content"], "Different seeds should produce different outputs"
    
    # But each seed should be deterministic for its own outputs
    result3 = llm_service1.process("Tell me a joke")
    assert result1["content"] == result3["content"], "Same seed should produce deterministic output"


def test_snapshot_testing():
    """Test snapshot-based testing for LLM outputs."""
    # Create a snapshot directory for testing
    test_snapshot_dir = Path("tests/snapshots/llm_responses_test")
    if not test_snapshot_dir.exists():
        test_snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    # Sample snapshot to compare against
    sample_snapshot = {
        "content": "This is a sample snapshot response",
        "model": "mock-model",
        "metadata": {"snapshot": True}
    }
    
    # Write sample snapshot to file
    input_hash = "test_hash_123"
    with open(test_snapshot_dir / f"{input_hash}.json", "w") as f:
        json.dump(sample_snapshot, f)
    
    # In the real test, we would use the actual LLMService with snapshot_mode=True
    # For this demo, we'll just verify the snapshot file exists
    assert (test_snapshot_dir / f"{input_hash}.json").exists(), "Snapshot file should exist"
    
    # Read back the snapshot and verify contents
    with open(test_snapshot_dir / f"{input_hash}.json", "r") as f:
        loaded_snapshot = json.load(f)
    
    assert loaded_snapshot == sample_snapshot, "Loaded snapshot should match original"
    
    # Clean up temporary test directory
    import shutil
    shutil.rmtree(test_snapshot_dir)


def test_assert_json_structure_only():
    """
    Demonstrate structure-only assertion for non-seeded models.
    
    When a model doesn't support seeding, we can still test the structure
    of the response (keys, types) without checking the exact content.
    """
    # Create service without seed (non-deterministic)
    llm_service = MockLLMService()
    
    # Get a response
    result = llm_service.process("Generate some JSON data")
    
    # Assert on structure, not content
    assert "content" in result, "Response should have content key"
    assert isinstance(result["content"], str), "Content should be a string"
    assert "model" in result, "Response should have model key"
    assert "metadata" in result, "Response should have metadata key"
    assert isinstance(result["metadata"], dict), "Metadata should be a dictionary"
    
    # When testing JSON output from an LLM, parse it and check keys
    # Here we're demonstrating with a fake JSON output
    sample_json_output = '{"name": "Product", "price": 42, "features": ["A", "B"]}'
    
    # In reality, this would come from the LLM
    parsed = json.loads(sample_json_output)
    
    # Test structure not exact values
    assert "name" in parsed, "Should have name key"
    assert "price" in parsed, "Should have price key"
    assert isinstance(parsed["price"], (int, float)), "Price should be numeric"
    assert "features" in parsed, "Should have features key"
    assert isinstance(parsed["features"], list), "Features should be a list"


def test_assert_with_cosine_similarity():
    """
    Demonstrate using embedding cosine similarity for testing.
    
    When exact output matching isn't possible but semantic closeness
    can be measured.
    """
    # Mock embedding function (in real test, use actual embedding model)
    def mock_embed(text):
        # Simple mock embedding function for demonstration
        import hashlib
        import numpy as np
        
        # Generate a deterministic but seemingly random vector based on text
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16) % 10**8
        np.random.seed(hash_val)
        return np.random.rand(1536)  # OpenAI embedding dimension
    
    # Mock cosine similarity function
    def cosine_similarity(vec1, vec2):
        import numpy as np
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    # Reference response we expect semantically similar answers to
    reference_text = "The capital of France is Paris, which is known for the Eiffel Tower."
    reference_embedding = mock_embed(reference_text)
    
    # Test text that's semantically similar
    similar_text = "Paris is the capital city of France, home to the iconic Eiffel Tower."
    similar_embedding = mock_embed(similar_text)
    
    # Test text that's semantically different
    different_text = "The Sahara Desert is the largest hot desert in the world."
    different_embedding = mock_embed(different_text)
    
    # Similar text should have high cosine similarity
    similar_score = cosine_similarity(reference_embedding, similar_embedding)
    
    # Different text should have low cosine similarity
    different_score = cosine_similarity(reference_embedding, different_embedding)
    
    # Assert that similar text has higher similarity than different text
    assert similar_score > different_score, "Similar text should have higher similarity"
    
    # In a real test, we would assert that the similarity is above a threshold
    similarity_threshold = 0.7  # Adjust based on your requirements
    # assert similar_score > similarity_threshold, f"Similarity score {similar_score} should be above {similarity_threshold}"


if __name__ == "__main__":
    # Create snapshots directory if it doesn't exist
    Path("tests/snapshots/llm_responses").mkdir(parents=True, exist_ok=True)
    
    # Run tests
    pytest.main(["-xvs", __file__])
