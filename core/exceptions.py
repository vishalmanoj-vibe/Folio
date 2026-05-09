# core/exceptions.py
"""
Custom exceptions for Folio.

Domain-specific exceptions for better error handling.
"""


class PortfolioDashboardError(Exception):
    """Base exception for Folio."""
    pass


class ValidationError(PortfolioDashboardError):
    """Raised when data validation fails."""
    pass


class DataHandlerError(PortfolioDashboardError):
    """Raised when CSV I/O operation fails."""
    pass


class MarketDataError(PortfolioDashboardError):
    """Raised when market data fetching fails."""
    pass


class ConfigurationError(PortfolioDashboardError):
    """Raised when configuration is invalid."""
    pass
