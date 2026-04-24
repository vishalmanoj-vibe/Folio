# test/test_csv_handler.py
"""
test/test_csv_handler.py
========================
Unit tests for csv_handler module.

Tests CSV loading, parsing, validation, and write operations.
"""

import os
import tempfile
import shutil
import pytest
import pandas as pd
from pathlib import Path


@pytest.fixture
def temp_csv_dir():
    """Create temporary directory for CSV testing."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def valid_csv_file(temp_csv_dir):
    """Create a valid CSV file for testing."""
    csv_path = os.path.join(temp_csv_dir, "test_transactions.csv")
    df = pd.DataFrame([
        ["buy", "VHY", 10, 81.50, "2026-01-15"],
        ["buy", "VAS", 5, 99.00, "2026-01-20"],
        ["sell", "VHY", 3, 85.00, "2026-02-01"],
    ], columns=["Type", "Ticker", "Shares", "Price", "Date"])
    df.to_csv(csv_path, index=False)
    return csv_path


class TestLoadCSV:
    """Test CSV loading functionality."""

    def test_load_valid_csv(self, valid_csv_file, monkeypatch):
        """Valid CSV should load successfully."""
        monkeypatch.setenv("PORTFOLIO_CSV", valid_csv_file)
        # Re-import to pick up new env var
        import importlib
        import data.csv_handler
        importlib.reload(data.csv_handler)
        from data.csv_handler import load_csv
        
        history = load_csv()
        assert len(history) == 3
        assert history[0]["ticker"] == "VHY"
        assert history[0]["type"] == "buy"
        assert float(history[0]["shares"]) == 10.0

    def test_load_csv_normalizes_column_names(self, temp_csv_dir, monkeypatch):
        """CSV with varied column names should normalize correctly."""
        csv_path = os.path.join(temp_csv_dir, "test.csv")
        df = pd.DataFrame([
            ["buy", "VHY", 10, 81.50, "2026-01-15"],
        ], columns=["TYPE", "  ticker  ", "SHARES", "price", "DATE"])
        df.to_csv(csv_path, index=False)
        
        monkeypatch.setenv("PORTFOLIO_CSV", csv_path)
        import importlib
        import data.csv_handler
        importlib.reload(data.csv_handler)
        from data.csv_handler import load_csv
        
        history = load_csv()
        assert len(history) == 1
        # Should handle case and whitespace normalization
        assert "ticker" in history[0]
        assert history[0]["ticker"] == "VHY"

    def test_load_csv_defaults_type_to_buy(self, temp_csv_dir, monkeypatch):
        """CSV without 'type' column should default to 'buy'."""
        csv_path = os.path.join(temp_csv_dir, "test.csv")
        df = pd.DataFrame([
            ["VHY", 10, 81.50, "2026-01-15"],
        ], columns=["Ticker", "Shares", "Price", "Date"])
        df.to_csv(csv_path, index=False)
        
        monkeypatch.setenv("PORTFOLIO_CSV", csv_path)
        import importlib
        import data.csv_handler
        importlib.reload(data.csv_handler)
        from data.csv_handler import load_csv
        
        history = load_csv()
        assert history[0]["type"] == "buy"

    def test_load_csv_supports_multiple_date_formats(self, temp_csv_dir, monkeypatch):
        """CSV should support YYYY-MM-DD and DD.MM.YYYY formats."""
        csv_path = os.path.join(temp_csv_dir, "test.csv")
        df = pd.DataFrame([
            ["buy", "VHY", 10, 81.50, "2026-01-15"],
            ["buy", "VAS", 5, 99.00, "15.01.2026"],  # DD.MM.YYYY
        ], columns=["Type", "Ticker", "Shares", "Price", "Date"])
        df.to_csv(csv_path, index=False)
        
        monkeypatch.setenv("PORTFOLIO_CSV", csv_path)
        import importlib
        import data.csv_handler
        importlib.reload(data.csv_handler)
        from data.csv_handler import load_csv
        
        history = load_csv()
        assert len(history) == 2
        # Both should be normalized to YYYY-MM-DD
        assert history[0]["date"] == "2026-01-15"
        assert history[1]["date"] == "2026-01-15"

    def test_load_csv_missing_file_raises(self, monkeypatch):
        """Missing CSV file should raise FileNotFoundError."""
        monkeypatch.setenv("PORTFOLIO_CSV", "/nonexistent/path/transactions.csv")
        import importlib
        import data.csv_handler
        importlib.reload(data.csv_handler)
        from data.csv_handler import load_csv
        
        with pytest.raises(FileNotFoundError):
            load_csv()

    def test_load_csv_missing_columns_raises(self, temp_csv_dir, monkeypatch):
        """CSV missing required columns should raise ValueError."""
        csv_path = os.path.join(temp_csv_dir, "test.csv")
        df = pd.DataFrame([
            ["VHY", 10, 81.50],  # Missing date
        ], columns=["Ticker", "Shares", "Price"])
        df.to_csv(csv_path, index=False)
        
        monkeypatch.setenv("PORTFOLIO_CSV", csv_path)
        import importlib
        import data.csv_handler
        importlib.reload(data.csv_handler)
        from data.csv_handler import load_csv
        
        with pytest.raises(ValueError, match="missing.*columns"):
            load_csv()

    def test_load_csv_invalid_numeric_values_raises(self, temp_csv_dir, monkeypatch):
        """CSV with invalid numeric values should raise ValueError."""
        csv_path = os.path.join(temp_csv_dir, "test.csv")
        df = pd.DataFrame([
            ["buy", "VHY", "not_a_number", 81.50, "2026-01-15"],
        ], columns=["Type", "Ticker", "Shares", "Price", "Date"])
        df.to_csv(csv_path, index=False)
        
        monkeypatch.setenv("PORTFOLIO_CSV", csv_path)
        import importlib
        import data.csv_handler
        importlib.reload(data.csv_handler)
        from data.csv_handler import load_csv
        
        with pytest.raises(ValueError):
            load_csv()


class TestSaveCSV:
    """Test CSV saving functionality."""

    def test_save_csv_creates_file(self, temp_csv_dir, monkeypatch):
        """save_csv should create CSV file."""
        csv_path = os.path.join(temp_csv_dir, "test.csv")
        monkeypatch.setenv("PORTFOLIO_CSV", csv_path)
        
        import importlib
        import data.csv_handler
        importlib.reload(data.csv_handler)
        from data.csv_handler import save_csv
        
        history = [
            {"type": "buy", "ticker": "VHY", "shares": 10, "price": 81.5, "date": "2026-01-15"},
        ]
        save_csv(history)
        
        assert Path(csv_path).exists()
        df = pd.read_csv(csv_path)
        assert len(df) == 1
        assert df.iloc[0]["Ticker"] == "VHY"

    def test_save_csv_creates_backup(self, temp_csv_dir, monkeypatch):
        """save_csv should create backup of existing CSV."""
        csv_path = os.path.join(temp_csv_dir, "test.csv")
        backup_path = f"{csv_path}.bak"
        monkeypatch.setenv("PORTFOLIO_CSV", csv_path)
        
        # Create initial CSV
        df = pd.DataFrame([
            ["buy", "VHY", 10, 81.50, "2026-01-15"],
        ], columns=["Type", "Ticker", "Shares", "Price", "Date"])
        df.to_csv(csv_path, index=False)
        
        import importlib
        import data.csv_handler
        importlib.reload(data.csv_handler)
        from data.csv_handler import save_csv
        
        # Save new data
        history = [
            {"type": "buy", "ticker": "VAS", "shares": 5, "price": 99.0, "date": "2026-01-20"},
        ]
        save_csv(history)
        
        # Backup should exist
        assert Path(backup_path).exists()
        # Backup should contain original data
        backup_df = pd.read_csv(backup_path)
        assert backup_df.iloc[0]["Ticker"] == "VHY"

    def test_save_csv_formats_correctly(self, temp_csv_dir, monkeypatch):
        """Saved CSV should have correct column names and format."""
        csv_path = os.path.join(temp_csv_dir, "test.csv")
        monkeypatch.setenv("PORTFOLIO_CSV", csv_path)
        
        import importlib
        import data.csv_handler
        importlib.reload(data.csv_handler)
        from data.csv_handler import save_csv
        
        history = [
            {"type": "buy", "ticker": "VHY", "shares": 10.5, "price": 81.50, "date": "2026-01-15"},
        ]
        save_csv(history)
        
        df = pd.read_csv(csv_path)
        expected_cols = ["Type", "Ticker", "Shares", "Price", "Date"]
        assert list(df.columns) == expected_cols
