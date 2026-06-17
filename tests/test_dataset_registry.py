import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.dataset_registry import list_datasets, resolve_dataset_name


def test_resolve_dataset_name_maps_supported_aliases():
    observed = {
        "lite": resolve_dataset_name("lite"),
        "verified": resolve_dataset_name("verified"),
        "full": resolve_dataset_name("full"),
        "multimodal": resolve_dataset_name("multimodal"),
        "multilingual": resolve_dataset_name("multilingual"),
    }
    expected = {
        "lite": "princeton-nlp/SWE-bench_Lite",
        "verified": "princeton-nlp/SWE-bench_Verified",
        "full": "princeton-nlp/SWE-bench",
        "multimodal": "princeton-nlp/SWE-bench_Multimodal",
        "multilingual": "SWE-bench/SWE-bench_Multilingual",
    }

    assert observed == expected


def test_resolve_dataset_name_preserves_raw_huggingface_ids():
    observed = resolve_dataset_name("custom-org/custom-dataset")
    expected = "custom-org/custom-dataset"

    assert observed == expected


def test_list_datasets_includes_supported_aliases():
    output = list_datasets()

    observed = {
        "has_lite": "lite" in output,
        "has_verified": "verified" in output,
        "has_full": "full" in output,
        "has_multimodal": "multimodal" in output,
        "has_multilingual": "multilingual" in output,
    }
    expected = {
        "has_lite": True,
        "has_verified": True,
        "has_full": True,
        "has_multimodal": True,
        "has_multilingual": True,
    }

    assert observed == expected
