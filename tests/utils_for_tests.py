import json
import string
from pathlib import Path
from typing import Any, Dict

import numpy as np


def random_jsonl_batch(tmp_path: Path, batch_size: int, seed: int = 42):
    rng = np.random.default_rng(seed)
    path = tmp_path / f"{random_string(rng, 8)}.json"

    with path.open("w") as f:
        for _ in range(batch_size):
            rec = random_record(rng)
            print(json.dumps(rec), file=f)
    return path


def random_record(rng: np.random.Generator) -> Dict[str, Any]:
    rec = {
        "a": int(rng.integers(0, 10)),
        "b": float(rng.random()),
        "c": random_string(rng, 32),
        "d": rng.normal(size=rng.integers(0, 100)).tolist(),
    }
    return rec


def random_string(rng: np.random.Generator, length: int):
    return "".join(rng.choice(list(string.ascii_letters), length))
