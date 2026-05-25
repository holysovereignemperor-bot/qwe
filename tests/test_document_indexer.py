import pytest
import os
import tempfile
from document_indexer import DocumentIndexer, tokenize


class TestTokenize:
    def test_basic(self):
        tokens = tokenize("Hello world code fix")
        assert "hello" in tokens
        assert "world" in tokens
        assert "code" in tokens
        assert "fix" in tokens

    def test_stop_words_removed(self):
        tokens = tokenize("the is a an to of")
        assert tokens == []

    def test_short_words_removed(self):
        tokens = tokenize("a b c de fg hello")
        assert "hello" in tokens
        assert "de" in tokens
        assert "fg" in tokens

    def test_special_chars(self):
        tokens = tokenize("hello-world foo_bar 123")
        assert "hello" in tokens
        assert "world" in tokens
        assert "foo_bar" in tokens
        assert "123" in tokens


class TestDocumentIndexer:
    def test_empty_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = DocumentIndexer(tmpdir)
            results = indexer.search("test query")
            assert results == []

    def test_index_and_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = DocumentIndexer(tmpdir)
            indexer.add_document("python_guide.txt", "Python programming language setup install guide tutorial")
            indexer.add_document("cooking.txt", "Recipe for pasta with tomato sauce and garlic bread")

            results = indexer.search("python programming")
            assert len(results) > 0
            assert results[0]["title"] == "python_guide.txt"

    def test_relevance_ranking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = DocumentIndexer(tmpdir)
            indexer.add_document("general.txt", "setup install configure deploy code")
            indexer.add_document("specific.txt", "setup install setup install setup configuration")

            results = indexer.search("setup install")
            assert len(results) >= 2
            assert results[0]["title"] == "specific.txt"

    def test_no_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = DocumentIndexer(tmpdir)
            indexer.add_document("test.txt", "hello world programming")
            results = indexer.search("quantum physics nuclear")
            assert results == []

    def test_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = DocumentIndexer(tmpdir)
            for i in range(10):
                indexer.add_document(f"doc{i}.txt", f"common keyword document number {i}")
            results = indexer.search("common keyword", limit=3)
            assert len(results) <= 3

    def test_score_is_float(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = DocumentIndexer(tmpdir)
            indexer.add_document("test.txt", "setup install code fix")
            results = indexer.search("setup code")
            if results:
                assert isinstance(results[0]["score"], float)
                assert results[0]["score"] > 0

    def test_empty_query(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = DocumentIndexer(tmpdir)
            indexer.add_document("test.txt", "hello world")
            results = indexer.search("")
            assert results == []
