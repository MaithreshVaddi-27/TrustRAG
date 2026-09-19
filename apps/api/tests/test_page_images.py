"""
Unit tests for OCR page-image persistence (Phase 7 residual).

RED: app/ingestion/page_images.py does not exist yet.
"""

from __future__ import annotations

import os

import pytest

from app.ingestion import page_images

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture
def image_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PAGE_IMAGES_DIR", str(tmp_path / "page_images"))
    return tmp_path / "page_images"


def test_save_returns_relative_ref_and_round_trips_bytes(image_dir):
    ref = page_images.save_page_image("kb1", "doc1", 2, PNG_BYTES)
    assert ref == os.path.join("kb1", "doc1", "p2.png")
    resolved = page_images.resolve_page_image_path(ref)
    assert resolved is not None
    assert resolved.read_bytes() == PNG_BYTES


def test_save_rejects_bad_inputs(image_dir):
    with pytest.raises(ValueError):
        page_images.save_page_image("../evil", "doc1", 1, PNG_BYTES)
    with pytest.raises(ValueError):
        page_images.save_page_image("kb1", "doc1", 0, PNG_BYTES)
    with pytest.raises(ValueError):
        page_images.save_page_image("kb1", "doc1", 1, b"")


def test_resolve_rejects_traversal_and_unknown(image_dir):
    assert page_images.resolve_page_image_path("../../etc/passwd") is None
    assert page_images.resolve_page_image_path("kb1/doc1/p9.png") is None
    assert page_images.resolve_page_image_path("") is None


def test_copy_remaps_ref_to_destination(image_dir):
    src = page_images.save_page_image("kb1", "doc1", 3, PNG_BYTES)
    dest = page_images.copy_page_image(src, "kb2", "doc2")
    assert dest == os.path.join("kb2", "doc2", "p3.png")
    assert page_images.resolve_page_image_path(dest).read_bytes() == PNG_BYTES
    # Source stays intact (snapshot shares nothing mutably).
    assert page_images.resolve_page_image_path(src).read_bytes() == PNG_BYTES


def test_copy_missing_source_returns_none(image_dir):
    assert page_images.copy_page_image("kb1/doc1/p1.png", "kb2", "doc2") is None


def test_delete_doc_removes_only_that_doc(image_dir):
    page_images.save_page_image("kb1", "doc1", 1, PNG_BYTES)
    page_images.save_page_image("kb1", "doc2", 1, PNG_BYTES)
    removed = page_images.delete_doc_page_images("kb1", "doc1")
    assert removed == 1
    assert page_images.resolve_page_image_path(os.path.join("kb1", "doc1", "p1.png")) is None
    assert page_images.resolve_page_image_path(os.path.join("kb1", "doc2", "p1.png")) is not None


def test_delete_kb_removes_whole_tree(image_dir):
    page_images.save_page_image("kb1", "doc1", 1, PNG_BYTES)
    page_images.save_page_image("kb1", "doc1", 2, PNG_BYTES)
    removed = page_images.delete_kb_page_images("kb1")
    assert removed == 2
    assert not (image_dir / "kb1").exists()
