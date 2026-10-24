"""Tests de `harness/credentials.py`: precedencia de fuentes y variables vacías. Sin modelo ni red."""

import os

import pytest

from harness import credentials
from harness.credentials import API_KEY, OAUTH_TOKEN, describe, detect, require_api_key

FAKE_KEY = "sk-ant-sintetica-0000"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(API_KEY, raising=False)
    monkeypatch.delenv(OAUTH_TOKEN, raising=False)


def test_environment_wins_over_dotenv(monkeypatch, tmp_path):
    monkeypatch.setenv(API_KEY, FAKE_KEY)
    (tmp_path / ".env").write_text(f"{API_KEY}=otra\n", encoding="utf-8")
    info = detect(tmp_path)
    assert info.api_key_available and "entorno" in info.source
    assert os.environ[API_KEY] == FAKE_KEY


def test_dotenv_fills_missing_key(tmp_path):
    (tmp_path / ".env").write_text(f"# comentario\n{API_KEY}=\"{FAKE_KEY}\"\n", encoding="utf-8")
    info = detect(tmp_path)
    assert info.api_key_available and ".env" in info.source
    assert os.environ[API_KEY] == FAKE_KEY  # la heredan la CLI y el cliente anthropic


def test_empty_variable_is_dropped(monkeypatch, tmp_path):
    monkeypatch.setenv(API_KEY, "  ")
    monkeypatch.setenv(OAUTH_TOKEN, "token-sintetico")
    info = detect(tmp_path)
    assert API_KEY not in os.environ
    assert not info.api_key_available
    assert OAUTH_TOKEN in info.source and "vacías" in info.source


def test_no_credential(tmp_path):
    info = detect(tmp_path)
    assert not info.api_key_available and "login" in info.source
    with pytest.raises(RuntimeError):
        require_api_key(tmp_path)


def test_describe_never_shows_the_key(monkeypatch, tmp_path):
    monkeypatch.setenv(API_KEY, FAKE_KEY)
    line = describe(detect(tmp_path))
    assert FAKE_KEY not in line
    assert credentials.SDK_VERSION in line and credentials.CLI_VERSION in line
