"""Helpers to build API payloads with only non-empty fields."""


def _is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def omit_empty_fields(value):
    """
    Recursively drop keys/items with no value (None, blank string, empty list/dict).
    Keeps 0, False, and other explicit falsy values that are still meaningful.
    """
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            pruned = omit_empty_fields(item)
            if not _is_empty(pruned):
                cleaned[key] = pruned
        return cleaned
    if isinstance(value, list):
        cleaned = [omit_empty_fields(item) for item in value]
        cleaned = [item for item in cleaned if not _is_empty(item)]
        return cleaned
    return value
