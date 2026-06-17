"""Dataset aliases for supported SWE-bench variants."""

from typing import Dict


DATASET_ALIASES: Dict[str, str] = {
    "full": "princeton-nlp/SWE-bench",
    "swe-bench": "princeton-nlp/SWE-bench",
    "swebench": "princeton-nlp/SWE-bench",
    "lite": "princeton-nlp/SWE-bench_Lite",
    "swe-bench-lite": "princeton-nlp/SWE-bench_Lite",
    "swebench-lite": "princeton-nlp/SWE-bench_Lite",
    "verified": "princeton-nlp/SWE-bench_Verified",
    "swe-bench-verified": "princeton-nlp/SWE-bench_Verified",
    "swebench-verified": "princeton-nlp/SWE-bench_Verified",
    "multimodal": "princeton-nlp/SWE-bench_Multimodal",
    "swe-bench-multimodal": "princeton-nlp/SWE-bench_Multimodal",
    "swebench-multimodal": "princeton-nlp/SWE-bench_Multimodal",
    "multilingual": "SWE-bench/SWE-bench_Multilingual",
    "swe-bench-multilingual": "SWE-bench/SWE-bench_Multilingual",
    "swebench-multilingual": "SWE-bench/SWE-bench_Multilingual",
}


DATASET_DESCRIPTIONS: Dict[str, str] = {
    "lite": "SWE-bench Lite - 300 lower-cost evaluation instances",
    "verified": "SWE-bench Verified - 500 human-filtered instances",
    "full": "SWE-bench Full - 2,294 original benchmark instances",
    "multimodal": "SWE-bench Multimodal - visual issue instances",
    "multilingual": "SWE-bench Multilingual - 300 tasks across 9 languages",
}


def resolve_dataset_name(dataset: str) -> str:
    """Return the Hugging Face dataset ID for a supported alias or raw ID."""
    if not dataset:
        return DATASET_ALIASES["lite"]

    normalized = dataset.strip()
    return DATASET_ALIASES.get(normalized.lower(), normalized)


def list_datasets() -> str:
    """Return a human-readable list of supported dataset aliases."""
    lines = ["Available SWE-bench datasets:"]
    for alias, description in DATASET_DESCRIPTIONS.items():
        lines.append(f"  {alias:<12} -> {DATASET_ALIASES[alias]:<36} {description}")
    lines.append("")
    lines.append("You can also pass a full Hugging Face dataset ID to --dataset.")
    return "\n".join(lines)
