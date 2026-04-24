# data/repository.py
import logging
from data.csv_handler import load_csv, save_csv

logger = logging.getLogger(__name__)

class PortfolioRepository:
    """
    Abstraction layer for portfolio data access.
    Currently uses CSV storage but can be extended to databases.
    """
    
    def load_transactions(self) -> list[dict]:
        """Load all transactions from storage."""
        return load_csv()

    def save_transactions(self, history: list[dict]) -> None:
        """Overwrite storage with full transaction history."""
        save_csv(history)

    def append_transaction(self, new_txn: dict) -> list[dict]:
        """Append a single transaction and return the updated history."""
        history = self.load_transactions()
        history.append(new_txn)
        self.save_transactions(history)
        return history
