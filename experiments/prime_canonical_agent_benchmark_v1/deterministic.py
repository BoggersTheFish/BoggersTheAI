"""Small deterministic primitives with no runtime randomness dependency."""

MASK64 = (1 << 64) - 1


def splitmix64(value: int) -> int:
    """Return one SplitMix64 output for an integer input."""
    z = (value + 0x9E3779B97F4A7C15) & MASK64
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
    return (z ^ (z >> 31)) & MASK64


def deterministic_bit(seed: int, index: int) -> int:
    """Generate a deterministic binary symbol."""
    value = splitmix64((seed & MASK64) ^ splitmix64(index & MASK64))
    return value & 1


def learner_draw(seed: int, index: int) -> int:
    """Deterministic pseudo-random 64-bit learner draw."""
    return splitmix64(
        (seed & MASK64)
        ^ 0xA0761D6478BD642F
        ^ splitmix64(index & MASK64)
    )
