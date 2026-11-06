from pathlib import Path

import pytest

from openwiki_graph.config import AppConfig, LLMConfig, load_config


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "openwiki-graph.toml"
    p.write_text(content)
    return p


def test_missing_file_returns_empty_config(tmp_path):
    cfg = load_config(tmp_path / "nonexistent.toml")
    assert isinstance(cfg, AppConfig)
    assert cfg.wiki.root == ""
    assert cfg.indexing.chunk_size is None
    assert cfg.indexing.chunk_overlap is None
    assert cfg.indexing.extraction_dir is None


def test_empty_file_returns_empty_config(tmp_path):
    p = _write(tmp_path, "")
    cfg = load_config(p)
    assert cfg.wiki.root == ""
    assert cfg.indexing.chunk_size is None


def test_wiki_root_parsed(tmp_path):
    p = _write(tmp_path, '[wiki]\nroot = "my-wiki"\n')
    assert load_config(p).wiki.root == "my-wiki"


def test_indexing_section_parsed(tmp_path):
    p = _write(tmp_path, "[indexing]\nchunk_size = 1024\nchunk_overlap = 100\nextraction_dir = \".cache\"\n")
    cfg = load_config(p)
    assert cfg.indexing.chunk_size == 1024
    assert cfg.indexing.chunk_overlap == 100
    assert cfg.indexing.extraction_dir == ".cache"


def test_full_config(tmp_path):
    toml = """
[wiki]
root = "openwiki"

[indexing]
extraction_dir = ".openwiki-graph"
chunk_size = 512
chunk_overlap = 50
"""
    cfg = load_config(_write(tmp_path, toml))
    assert cfg.wiki.root == "openwiki"
    assert cfg.indexing.extraction_dir == ".openwiki-graph"
    assert cfg.indexing.chunk_size == 512
    assert cfg.indexing.chunk_overlap == 50


def test_unknown_section_raises(tmp_path):
    p = _write(tmp_path, "[typo]\nfoo = 1\n")
    with pytest.raises(ValueError, match="unknown section"):
        load_config(p)


def test_invalid_toml_raises(tmp_path):
    p = _write(tmp_path, "this is not = = valid toml ][")
    with pytest.raises(ValueError, match="Could not parse"):
        load_config(p)


def test_chunk_size_wrong_type_raises(tmp_path):
    p = _write(tmp_path, '[indexing]\nchunk_size = "big"\n')
    with pytest.raises(ValueError, match="chunk_size must be an integer"):
        load_config(p)


def test_partial_indexing_section(tmp_path):
    p = _write(tmp_path, "[indexing]\nchunk_size = 256\n")
    cfg = load_config(p)
    assert cfg.indexing.chunk_size == 256
    assert cfg.indexing.chunk_overlap is None  # not set → indexer uses env/default


def test_stores_section_parsed(tmp_path):
    toml = '[stores]\ngraph = "bolt://localhost:7687"\nvector = "postgresql://localhost/mydb"\n'
    cfg = load_config(_write(tmp_path, toml))
    assert cfg.stores.graph == "bolt://localhost:7687"
    assert cfg.stores.vector == "postgresql://localhost/mydb"


def test_stores_defaults_to_empty_strings(tmp_path):
    cfg = load_config(tmp_path / "nonexistent.toml")
    assert cfg.stores.graph == ""
    assert cfg.stores.vector == ""


def test_stores_partial_section(tmp_path):
    p = _write(tmp_path, '[stores]\ngraph = "bolt://neo4j:7687"\n')
    cfg = load_config(p)
    assert cfg.stores.graph == "bolt://neo4j:7687"
    assert cfg.stores.vector == ""


def test_llm_defaults_to_bedrock(tmp_path):
    cfg = load_config(tmp_path / "nonexistent.toml")
    assert cfg.llm.provider == "bedrock"
    assert cfg.llm.model == ""
    assert cfg.llm.embed_model == ""
    assert cfg.llm.base_url == ""


def test_llm_section_parsed(tmp_path):
    toml = '[llm]\nprovider = "openai"\nmodel = "gpt-4o"\nembed_model = "text-embedding-3-large"\n'
    cfg = load_config(_write(tmp_path, toml))
    assert cfg.llm.provider == "openai"
    assert cfg.llm.model == "gpt-4o"
    assert cfg.llm.embed_model == "text-embedding-3-large"


def test_llm_ollama_with_base_url(tmp_path):
    toml = '[llm]\nprovider = "ollama"\nmodel = "llama3.2"\nbase_url = "http://myhost:11434"\n'
    cfg = load_config(_write(tmp_path, toml))
    assert cfg.llm.provider == "ollama"
    assert cfg.llm.base_url == "http://myhost:11434"


def test_llm_unknown_provider_raises(tmp_path):
    p = _write(tmp_path, '[llm]\nprovider = "mistral"\n')
    with pytest.raises(ValueError, match="not supported"):
        load_config(p)


def test_full_config_with_stores(tmp_path):
    toml = """
[wiki]
root = "openwiki"

[stores]
graph = "bolt://user:pass@localhost:7687"
vector = "postgresql://user:pass@localhost:5432/db"

[indexing]
extraction_dir = ".openwiki-graph"
chunk_size = 512
chunk_overlap = 50
"""
    cfg = load_config(_write(tmp_path, toml))
    assert cfg.wiki.root == "openwiki"
    assert cfg.stores.graph == "bolt://user:pass@localhost:7687"
    assert cfg.stores.vector == "postgresql://user:pass@localhost:5432/db"
    assert cfg.indexing.chunk_size == 512
