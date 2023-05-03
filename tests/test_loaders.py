import json
import time
from pathlib import Path

import pytest

from elbow import as_record, load_parquet, load_table
from elbow.extractors import file_meta
from elbow.typing import StrOrPath
from tests.utils_for_tests import random_jsonl_batch

NUM_BATCHES = 64
BATCH_SIZE = 256
SEED = 2022

# TODO: may want to benchmark these with pytest-benchmark


@pytest.fixture(scope="module")
def mod_tmp_path(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("tmp")


@pytest.fixture(scope="module")
def jsonl_dataset(mod_tmp_path: Path) -> str:
    for ii in range(NUM_BATCHES):
        random_jsonl_batch(mod_tmp_path, BATCH_SIZE, seed=(SEED + ii))

    pattern = str(mod_tmp_path / "*.json")
    return pattern


def extract_jsonl(path: StrOrPath):
    metadata = as_record(file_meta(path))

    with open(path) as f:
        for line in f:
            record = json.loads(line)
            # with metadata
            record = metadata + record
            yield record


def test_load_table(jsonl_dataset: str):
    df = load_table(source=jsonl_dataset, extract=extract_jsonl)
    assert df.shape == (NUM_BATCHES * BATCH_SIZE, 7)

    expected_columns = ["file_path", "link_target", "mod_time", "a", "b", "c", "d"]
    assert df.columns.tolist() == expected_columns


def test_load_parquet(jsonl_dataset: str, mod_tmp_path: Path):
    pq_path = mod_tmp_path / "dset.parquet"

    dset = load_parquet(
        source=jsonl_dataset,
        extract=extract_jsonl,
        where=pq_path,
    )
    assert len(dset.files) == 1

    df = dset.read().to_pandas()
    assert df.shape == (NUM_BATCHES * BATCH_SIZE, 7)

    with pytest.raises(FileExistsError):
        load_parquet(
            source=jsonl_dataset,
            extract=extract_jsonl,
            where=pq_path,
        )

    # Re-write batch 0
    random_jsonl_batch(mod_tmp_path, BATCH_SIZE, seed=SEED)
    # New batch
    random_jsonl_batch(mod_tmp_path, BATCH_SIZE, seed=(SEED + NUM_BATCHES))

    # NOTE: have to wait at least a second to avoid clobbering the previous partition.
    time.sleep(1.0)

    dset2 = load_parquet(
        source=jsonl_dataset,
        extract=extract_jsonl,
        where=pq_path,
        incremental=True,
    )
    assert len(dset2.files) == 2

    df2 = dset2.read().to_pandas()
    assert df2.shape == ((NUM_BATCHES + 2) * BATCH_SIZE, 7)


def test_load_parquet_parallel(jsonl_dataset: str, mod_tmp_path: Path):
    pq_path = mod_tmp_path / "dset_parallel.parquet"

    dset = load_parquet(
        source=jsonl_dataset,
        extract=extract_jsonl,
        where=pq_path,
        workers=2,
    )
    assert len(dset.files) == 2

    df = dset.read().to_pandas()
    # NOTE: only + 1 bc the new batch is no longer new
    assert df.shape == ((NUM_BATCHES + 1) * BATCH_SIZE, 7)


if __name__ == "__main__":
    pytest.main([__file__])
