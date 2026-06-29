import pytest

from criadex.index.ragflow_objects.chat import RagflowChatAgent


def test_normalize_dialog_id_hashes_non_hex_ids():
    raw = "gradebook-mapper-13d85e044aea"
    normalized = RagflowChatAgent._normalize_dialog_id(raw)
    assert len(normalized) == 32
    assert normalized != raw


def test_normalize_dialog_id_preserves_hex32_ids():
    raw = "fa74627f81dc1d548850020555edf5fe"
    normalized = RagflowChatAgent._normalize_dialog_id(raw)
    assert normalized == raw


def test_normalize_dialog_id_hashes_uuid36_ids():
    raw = "018999d1-610e-471c-826a-16bbfb0b171d"
    normalized = RagflowChatAgent._normalize_dialog_id(raw)
    assert len(normalized) == 32
    assert normalized != raw
