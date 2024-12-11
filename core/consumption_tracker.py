"""Consumption tracking for API and resource usage."""

import pandas as pd

class ConsumptionTracker:
    """An asynchronous context manager that tracks and guarantees the saving of API consumption data.
    
    Each consumption record must contain:
    - client: str, the client identifier
    - search_date: datetime in microseconds precision (datetime[us])
    - function: str, name of the function that consumed the API
    - model: str, name of the model used
    - search_calls: int, number of search API calls made
    - input_tokens: int, number of input tokens used
    - output_tokens: int, number of output tokens used
    """

    def __init__(self, app, client):
        """
        Initialize the consumption tracker.
        
        Args:
            app (WebResearchApp): Main application instance
            client (str): Client identifier
        """
        self.app = app
        self.client = client
        self.consumptions = []
        # Store creation time in microsecond precision
        self.search_date = pd.Timestamp.now().floor('us')

    async def __aenter__(self):
        """Enter the async context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context and save all consumption data."""
        if self.consumptions:
            try:
                df = pd.DataFrame(self.consumptions)
                self.app.storage_manager.append_to_parquet(
                    df,
                    'consumption.parquet',
                    self.client
                )
            except Exception as e:
                self.app.logger.error(f"Failed to save consumption data: {str(e)}")
                raise

    def add_consumption(self, consumption_data):
        """Add consumption data to the tracker."""
        if isinstance(consumption_data, list):
            for record in consumption_data:
                processed_record = self._process_record(record)
                self.consumptions.append(processed_record)
        else:
            processed_record = self._process_record(consumption_data)
            self.consumptions.append(processed_record)

    def _process_record(self, record):
        """Process a single consumption record to ensure it has all required fields."""
        if not isinstance(record, dict):
            raise ValueError("Consumption record must be a dictionary")

        # Add client and search_date if missing
        record['client'] = record.get('client', self.client)
        record['search_date'] = record.get('search_date', self.search_date)

        # Validate required fields
        required_fields = ['function', 'model', 'search_calls', 'input_tokens', 'output_tokens']
        missing_fields = [field for field in required_fields if field not in record]
        if missing_fields:
            raise ValueError(f"Missing required fields in consumption record: {missing_fields}")

        return record
