"""Consumption tracking for API and resource usage."""

import pandas as pd

class ConsumptionTracker:
    """
    An asynchronous context manager that tracks and guarantees the saving of API consumption data.
    
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
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the async context and save all consumption data.
        Ensures all data has proper client and search_date fields in microsecond precision.
        """
        if self.consumptions:
            # Create DataFrame from collected consumption data
            df_consumption = pd.DataFrame(self.consumptions)
            
            # Ensure datetime precision is microseconds
            if 'search_date' in df_consumption.columns:
                df_consumption['search_date'] = pd.to_datetime(df_consumption['search_date']).dt.floor('us')
            else:
                df_consumption['search_date'] = self.search_date
            
            # Ensure client field exists
            if 'client' not in df_consumption.columns:
                df_consumption['client'] = self.client
                
            # Reorder columns to ensure client and search_date are first
            columns = ['client', 'search_date'] + [col for col in df_consumption.columns 
                                                 if col not in ['client', 'search_date']]
            df_consumption = df_consumption[columns]
            
            # Append to parquet file
            consumption_filepath = f"{self.client}/{self.app.config['DF_CONSUMPTION_FILENAME']}"
            self.app.storage_manager.append_to_parquet(df_consumption, consumption_filepath)
            
    def add_consumption(self, consumption_data):
        """
        Add consumption data to the tracker.
        
        Args:
            consumption_data (Union[dict, list]): Single consumption record or list of records.
            Each record must include function, model, search_calls, input_tokens, and output_tokens.
            Client and search_date will be added automatically if missing.
            
        Example consumption record:
        {
            'client': 'client_name',  # Optional, added if missing
            'search_date': pd.Timestamp('2024-10-25 12:34:56.123456'),  # Optional, added if missing
            'function': 'search_proposal_agent',
            'model': 'gpt-4',
            'search_calls': 0,
            'input_tokens': 100,
            'output_tokens': 50
        }
        """
        if isinstance(consumption_data, list):
            # Process list of consumption records
            for record in consumption_data:
                processed_record = self._process_record(record)
                self.consumptions.append(processed_record)
        else:
            # Process single consumption record
            processed_record = self._process_record(consumption_data)
            self.consumptions.append(processed_record)
    
    def _process_record(self, record):
        """
        Process a single consumption record to ensure it has all required fields.
        
        Args:
            record (dict): The consumption record to process
            
        Returns:
            dict: Processed record with all required fields
        """
        processed = record.copy()
        
        # Add client if missing
        if 'client' not in processed:
            processed['client'] = self.client
            
        # Add or normalize search_date
        if 'search_date' not in processed:
            processed['search_date'] = self.search_date
        else:
            # Ensure microsecond precision
            processed['search_date'] = pd.to_datetime(processed['search_date']).floor('us')
            
        # Validate required fields
        required_fields = ['function', 'model', 'search_calls', 'input_tokens', 'output_tokens']
        missing_fields = [field for field in required_fields if field not in processed]
        if missing_fields:
            raise ValueError(f"Consumption record missing required fields: {missing_fields}")
            
        return processed
