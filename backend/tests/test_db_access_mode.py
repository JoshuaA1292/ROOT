"""Tests for MongoDB repository/MCP access-mode bridge."""
from app.db import access_mode


def test_load_mongodb_mcp_config_resolves_env(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb+srv://example")
    monkeypatch.setenv("MONGODB_DB", "root_test")
    monkeypatch.setattr(access_mode.settings, "mongodb_mcp_config_path", "mcp/mcp.config.json")

    config = access_mode.load_mongodb_mcp_config()

    assert config["name"] == "mongodb"
    assert config["command"] == "npx"
    assert "@mongodb-js/mongodb-mcp-server" in config["args"]
    assert config["env"]["MONGODB_URI"] == "mongodb+srv://example"
    assert config["env"]["MONGODB_DATABASE"] == "root_test"


def test_invalid_access_mode_falls_back_to_repository(monkeypatch):
    monkeypatch.setattr(access_mode.settings, "mongodb_access_mode", "bad")

    assert access_mode.mongodb_access_mode() == "repository"
