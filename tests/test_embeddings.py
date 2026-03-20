from __future__ import annotations

from BoggersTheAI.core.embeddings import (
    OllamaEmbedder,
    batch_cosine_matrix,
    cosine_similarity,
)


def test_cosine_identical_vectors():
    v = [1.0, 0.0, 0.0]
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-6


def test_cosine_orthogonal_vectors():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(cosine_similarity(a, b)) < 1e-6


def test_cosine_empty_vectors():
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0], []) == 0.0


def test_cosine_mismatched_length():
    assert cosine_similarity([1.0, 2.0], [1.0]) == 0.0


def test_cosine_negative():
    a = [1.0, 0.0]
    b = [-1.0, 0.0]
    assert cosine_similarity(a, b) < 0


def test_batch_cosine_matrix():
    embeddings = {
        "a": [1.0, 0.0],
        "b": [0.0, 1.0],
        "c": [1.0, 1.0],
    }
    matrix = batch_cosine_matrix(embeddings)
    assert "a" in matrix
    assert "b" in matrix["a"]
    assert abs(matrix["a"]["b"]) < 1e-6


def test_embedder_init():
    embedder = OllamaEmbedder(model="test-model")
    assert embedder.model == "test-model"
