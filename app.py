#======================================================================================
# WebResearchApp
#======================================================================================

from core.storage_manager import StorageManager
from core.client_manager import ClientManager
from core.data_manager import DataManager  # For data handling
from config.logger_config import LoggerConfig, NewFileForEachRunHandler, ErrorAction

import logging
import os
import sys
import inspect # For getting the calling frame
import asyncio # For async ops
from aiolimiter import AsyncLimiter # For rate limiting
import yaml  # For config file reading
import pandas as pd  # For DataFrame handling
from datetime import datetime  # For date handling in pricing
from pathlib import Path  # For path handling
from dotenv import load_dotenv # For loading environment variables

class WebResearchApp:

    """
    Main application class for web research and data processing.

    This class manages the overall execution of the web research application,
    including configuration loading, logging setup, client management, and
    API cost calculation.

    Attributes:
        working_directory (str): The working directory for the application.
        loggerconfig (LoggerConfig): Configuration for logging.
        logger (logging.Logger): Logger instance for the application.
        config (dict): Application configuration loaded from YAML file.
        client_managers (List[ClientManager]): List of client manager instances.
        df_prices (pd.DataFrame): DataFrame containing API pricing data.

    Methods:
        setup_logging(): Set up and configure the logging system.
        handle_error(): Handle errors based on their severity level.
        read_config_app(): Read and validate configuration from a YAML file.
        create_client_managers(): Create ClientManager instances for each valid client directory.
        load_pricing_data(): Load pricing data from an Excel file.
        check_pricing_sequentiality(): Check the sequentiality of pricing data.
        get_price(): Get the applicable price for a given model, date, and price type.
        calculate_api_costs(): Calculate API costs based on consumption data.
        run(): Main execution method for the WebResearchApp.

    The class orchestrates the entire process of web research, including
    data loading, client processing, and cost calculation.
    """

    def __init__(self, working_directory=None):

        # get working directory if given one.
        self.working_directory = working_directory

        # establish Storage, uses bootstrip config, we load actual config later.
        self.storage_manager = StorageManager(self)
        # print("etablished storage manager")

        # if working direcotry is None, then we use boot strapped working directory
        if self.working_directory is None:
            self.working_directory = self.storage_manager.working_directory
        
        print(f"Working dir {self.working_directory}")

        # setup logging
        self.loggerconfig = LoggerConfig()
        self.logger = self.setup_logging()
        # print("etablished logger")

        # read config file from working directory
        self.config = self.read_config_app()
        self.client_managers = []
        # print("etablished config file")

        # setup LLM prices
        self.df_prices = None

        # get today's date
        self.today = datetime.now()

        #self.client_managers = []

    # create log file
    def setup_logging(self):
        """
        Set up and configure the logging system for the application.

        This method creates a logger with the following characteristics:
        - Logger name: "app"
        - Log level: DEBUG (captures all log levels)
        - Handler: NewFileForEachRunHandler (creates a new log file for each run)
        - Log format: timestamp - logger name - log level - message

        Returns:
            logging.Logger: Configured logger object for the application.
        """
        import logging
        logger = logging.getLogger("app")
        logger.setLevel(logging.DEBUG)
        
        # Create a new file for each run handler
        file_handler = NewFileForEachRunHandler(
            app=self,  # Pass the entire app instance
            filename=self.loggerconfig.log_file,
            max_files=10
        )
        file_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
    
        return logger

    def handle_error(self, error_level, message, exception=None):
        """
        Handle errors based on their severity level and configured actions.

        This method logs the error with context information, determines the appropriate
        action based on the error level, and executes that action (ignore, retry, or terminate).

        Args:
            error_level (int): The severity level of the error (e.g., logging.ERROR, logging.CRITICAL).
            message (str): A descriptive message about the error.
            exception (Exception, optional): The exception object if one was raised.

        Returns:
            None

        Side Effects:
            - Logs the error message and context.
            - May retry the operation or terminate the application based on the error level.
        """
        # Get the calling frame (which function/object submitted the logged item)

        frame = inspect.currentframe().f_back
        func_name = frame.f_code.co_name
        file_name = frame.f_code.co_filename
        line_no = frame.f_lineno

        # Construct the context message
        context_message = f"Error occurred in function '{func_name}' in file '{file_name}' at line {line_no}"
        full_message = f"{context_message}\nError message: {message}"

        if exception:
            self.logger.exception(full_message)  # This logs the full stack trace
        else:
            self.logger.log(error_level, full_message)

        action = self.loggerconfig.error_actions.get(error_level, ErrorAction.IGNORE)
        
        if action == ErrorAction.IGNORE:
            return
        elif action == ErrorAction.RETRY:
            self.retry_operation(self.logger, error_level, full_message, exception)
        elif action == ErrorAction.TERMINATE:
            self.logger.critical(f"{context_message}\nApplication is terminating due to critical error.")
            sys.exit(1)

    def retry_operation(self, loggerconfig, logger, error_level, message, exception):
        for attempt in range(loggerconfig.max_retries):
            try:
                # Attempt the operation again
                # This is a placeholder for the actual retry logic
                logger.info(f"Retrying operation, attempt {attempt + 1}")
                # If successful, break out of the retry loop
                break
            except Exception as e:
                if attempt == loggerconfig.max_retries - 1:
                    logger.error(f"Max retries reached. Operation failed: {message}", exc_info=True)
                    # Optionally terminate here if max retries are reached
                    # sys.exit(1)

    def read_config_app(self, config_file_path= 'app_data/config_app.yaml')                  :
        """
        Read and validate configuration from a YAML file.

        This method reads the application configuration from a YAML file, validates
        the presence and format of required keys, and handles any errors encountered
        during the process.

        Args:
            config_file_path (str): Path to the YAML configuration file. 
                                    Defaults to 'app_data/config_app.yaml'.

        Returns:
            Dict[str, Any]: A dictionary containing the validated configuration.
                            Returns an empty dictionary if critical errors are encountered.

        Raises:
            No exceptions are raised directly. All errors are logged using self.handle_error().

        Note:
            - All errors encountered while reading the app's config file are treated as 'critical'.
            - The method checks for the existence and readability of the file, valid YAML format,
              presence of required keys, and correct data types for specific fields.
            - The 'DEBUG' flag must be explicitly set to True or False in the configuration.
        """
        config = {}

        # Note, all errors for reading the app's config file are 'critical'.
        
        if not self.storage_manager.file_exists(config_file_path):
            self.handle_error(self.logger, logging.CRITICAL, f"Configuration file not found: {config_file_path}")
            return config
        
        config_content = self.storage_manager.read_file(config_file_path)
        
        try:
            config = yaml.safe_load(config_content)
        except yaml.YAMLError as e:
            self.handle_error(self.logger, logging.CRITICAL, f"Error parsing YAML configuration file for {config_file_path}: {str(e)}")
            return config


        if not isinstance(config, dict):
            self.handle_error(self.logger, logging.CRITICAL,"Configuration file must contain a YAML dictionary")
            return {}
        
        # Validate required configuration items
        required_keys_strings = [#'WORKING_DIRECTORY', 
                        'DF_SEARCH_HISTORY_FILENAME',
                        'DF_SEARCH_HISTORY_UPDATES_FILENAME',
                        'DF_SEARCH_TASKS_FILENAME', 
                        'DF_CONSUMPTION_FILENAME', 
                        'API_PRICING_FILENAME', 
                        'SUBSCRIPTIONS_FILENAME',
                        'EMAIL_TEMPLATE_FILENAME',
                        'EMAIL_TEMPLATE_SPREADSHEET_FILENAME',
                        'BUSINESS_DESCRIPTION_FILENAME']

        for key in required_keys_strings:
            if key not in config:
                self.handle_error(self.logger, logging.CRITICAL,f"Missing required configuration key: {key}")
            elif not isinstance(config[key], str) or not config[key].strip():
                self.handle_error(self.logger, logging.CRITICAL,f"'{key}' must be a non-empty string")

        # APP cannot ber permitted to run if we are not sure whether in DEBUG mode or not, so use ASSERT statement...
        if not config['DEBUG'] in [True, False]: 
            self.handle_error(self.logger, logging.CRITICAL, "Must specify DEBUG as either True or False")

        return config

    def create_client_managers(self, subscriptions_file):
        """
        Create tasks for active clients based on the subscriptions file. No active subscription means no tasks.

        Args:
            subscriptions_file (str): Path to the subscriptions Excel file.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing client information and folder paths.
        """
        
        try:
            subscriptions_df = self.storage_manager.read_excel(subscriptions_file)
            # print("read subscriptions file")
        except Exception as e:
            # print(""couldnt read subscriptions file: {e}")
            self.handle_error(self.logger, logging.CRITICAL,f"Error reading subscriptions file: {str(e)}")
            return []
        
        if subscriptions_df.empty:
            # print("subs is empty")
            self.handle_error(self.logger, logging.CRITICAL,f"No data found in subscriptions file")
            return []
        
        today = self.today.date()
        # print("'Today is {today}')

        for _, row in subscriptions_df.iterrows():
            client = row.get('client')
            # print("'Client is {client}')
            if not client:
                self.handle_error(self.logger, logging.WARNING,f"Skipping row due to missing client {client}. Name: {row}")
                continue
            
            start_date = row.get('start_date').date() if pd.notna(row.get('start_date')) else None
            end_date = row.get('end_date').date() if pd.notna(row.get('end_date')) else None

            # print("'Start date is {start_date}, end date is {end_date}')
            if ( start_date and start_date <= today and 
                (end_date is None or end_date >= today)):
                client_monthly_budget = row.get('monthly_budget')
                client_manager = ClientManager(self, client=client, client_monthly_budget=float(client_monthly_budget), today=today)
                if not client_manager.any_errors:
                    self.client_managers.append(client_manager)

        self.logger.info(f"Created {len(self.client_managers)} client tasks")
        return

    def timing_decorator(self, func          ):
        """
        A DECORATOR that logs the start and end time of the decorated function,
        as well as its total execution time. If an exception occurs, it logs
        the error and the time at which the function failed.

        Args:
            func (Callable): The function to be decorated.

        Returns:
            Callable: The wrapped function with timing and logging capabilities.

        Raises:
            Exception: Any exception raised by the decorated function is re-raised
                       after logging.
        """
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            self.logger.info(f"Starting {func.__name__}...")
            try:
                result = await func(*args, **kwargs)
                end_time = time.time()
                self.logger.info(f"{func.__name__} completed in {end_time - start_time:.2f} seconds")
                return result
            except Exception as e:
                end_time = time.time()
                msg = f"{func.__name__} failed after {end_time - start_time:.2f} seconds with error: {str(e)}"
                self.handle_error(self.logger, logging.CRITICAL, msg)
                raise
        return wrapper


    def load_pricing_data(self, file_path):
        """
        Load pricing data from an Excel file and store it in self.df_prices.
        
        Args:
        file_path (str): Path to the Excel file containing pricing data.
        
        Returns:
        pandas.DataFrame or None: Loaded pricing data with datetime columns if successful, None otherwise.
        
        Raises:
        No exceptions are raised directly. All errors are logged using self.handle_error().
        
        Side Effects:
        - Sets self.df_prices if loading is successful.
        - Logs warnings or errors using self.handle_error().
        """
        try:           
            df_prices = self.storage_manager.read_excel(file_path)            
            
            if df_prices.empty:
                raise pd.errors.EmptyDataError("The pricing file is empty.")
            
            df_prices['start_date'] = pd.to_datetime(df_prices['start_date'], errors='coerce')
            df_prices['end_date'] = pd.to_datetime(df_prices['end_date'], errors='coerce')
            
            if df_prices['start_date'].isna().any():
                self.logger.warning("Some start dates could not be parsed. Please check your data.")
            
            self.df_prices = df_prices
            return df_prices
        except FileNotFoundError as e:
            msg=f"load_pricing_data, FileNotFoundError: {str(e)}"
            self.handle_error(self.logger, logging.CRITICAL, msg)
        except pd.errors.EmptyDataError as e:
            msg=f"load_pricing_data EmptyDataError: {str(e)}"
            self.handle_error(self.logger, logging.CRITICAL, msg)
        except Exception as e:
            msg=f"load_pricing_data, unexpected error occurred while reading the pricing file: {str(e)}"
            self.handle_error(self.logger, logging.CRITICAL, msg)
        
        return None

    def check_pricing_sequentiality(self):
        """
        Check the sequentiality of pricing data and log warnings for any issues.

        This method iterates through the pricing data for each unique model and checks for:
        1. Open-ended pricing periods (missing end dates)
        2. Gaps between consecutive pricing periods

        It logs warnings for open-ended periods and information about any gaps found.

        Note:
        - Requires self.df_prices to be loaded with pricing data.
        - Uses self.logger for logging messages.

        Raises:
            No exceptions are raised, but an error is logged if pricing data is not loaded.
        """
        if self.df_prices is None:
            self.logger.error("Pricing data not loaded. Call load_pricing_data first.")
            return

        for model in self.df_prices['model'].unique():
            model_df = self.df_prices[self.df_prices['model'] == model].sort_values('start_date')
            self.logger.info(f"Checking pricing for model: {model}")
            
            for i in range(len(model_df) - 1):
                current_end = model_df.iloc[i]['end_date']
                next_start = model_df.iloc[i+1]['start_date']
                
                if pd.isna(current_end):
                    self.logger.warning(f"Open-ended period found for {model} starting {model_df.iloc[i]['start_date']}")
                elif current_end < next_start:
                    self.logger.info(f"Gap found between price periods for {model}: {current_end} to {next_start}")
        
        self.logger.info("Pricing sequentiality check completed.")

    def get_price(self, model, date, price_type):
        """
        Get the applicable price for a given model, date, and price type.
        
        Args:
        model (str): The model name.
        date (datetime): The date for which to get the price.
        price_type (str): The type of price to retrieve (e.g., 'input_price').
        
        Returns:
        float: The applicable price, or None if no price is found.
        """
        if self.df_prices is None:
            self.logger.error("Pricing data not loaded. Call load_pricing_data first.")
            return None

        model_prices = self.df_prices[self.df_prices['model'] == model]
        valid_prices = model_prices[
            (model_prices['start_date'] <= date) & 
            ((model_prices['end_date'] >= date) | (model_prices['end_date'].isna()))
        ]
        
        if len(valid_prices) == 0:
            previous_prices = model_prices[model_prices['start_date'] <= date]
            if len(previous_prices) > 0:
                return previous_prices.iloc[-1][price_type]
            return None
        
        return valid_prices.iloc[-1][price_type]

    def calculate_api_costs(self, consumption_filename, client, date_from=None, date_to=None):
        """
        Load pricing and consumption data, calculate API costs, and save results.
        
        Args:
        consumption_filename (str): Path to the CSV file containing consumption data.
        client (str): Name of the client for which costs are being calculated.
        sample_size (int): Sample size used in the calculation.
        date_from (str, optional): Start date for cost calculation (format: 'YYYY-MM-DD').
        date_to (str, optional): End date for cost calculation (format: 'YYYY-MM-DD').
        
        Returns:
        pandas.DataFrame: Calculated costs per model per day.
        """
        try:
            if self.df_prices is None:
                self.logger.error("Pricing data not loaded. Call load_pricing_data first.")
                return None

            # Load consumption data
            df_consumption = self.storage_manager.read_parquet(consumption_filename, client=client)
            # print('loaded consumption data')
            # Check for models in consumption data not present in pricing data
            consumption_models = set(df_consumption['model'].unique())
            pricing_models = set(self.df_prices['model'].unique())
            missing_models = consumption_models - pricing_models
            missing_models_text = ', '.join(missing_models)
            if missing_models:
                msg = f"The following models are present in consumption data but missing from pricing data: {missing_models_text}"
                self.logger.error(msg)
            
            # Convert date strings to datetime objects if provided
            if date_from:
                date_from = pd.to_datetime(date_from)
            if date_to:
                date_to = pd.to_datetime(date_to)
            
            # Filter consumption data based on date range
            if date_from or date_to:
                mask = pd.Series(True, index=df_consumption.index)
                if date_from:
                    mask &= df_consumption['search_date'] >= date_from
                if date_to:
                    mask &= df_consumption['search_date'] <= date_to
                df_consumption = df_consumption[mask]
            
            # print("After filtered consumption data")
            # print("date_from type:", type(date_from))
            # Calculate costs
            results = []
            for _, row in df_consumption.iterrows():
                model = row['model']
                date = row['search_date']
                daily_cost = 0
                
                for price_type, token_type in [('input_price', 'input_tokens'), 
                                               ('output_price', 'output_tokens'), 
                                               ('search_price', 'search_calls')]:
                    price = self.get_price(model, date, price_type)
                    if price:
                        cost = (row[token_type] / 1e6) * price if 'tokens' in token_type else row[token_type] * price
                        daily_cost += cost
                
                results.append({
                    'date': date,
                    'model': model,
                    'cost': daily_cost
                })

            costs_df = pd.DataFrame(results)
            
            # if no results in data range...
            if len(costs_df) == 0:
                # create a blank dataframe with correct types for returning to caller
                costs_df = pd.DataFrame(columns=['date', 'model', 'cost'])
                costs_df['date']  = pd.to_datetime(costs_df['date'])
                costs_df['model'] = costs_df['model'].astype('str')
                costs_df['cost']  = costs_df['cost'].astype('float')
                # get values for save filename
                start_date = date_from.strftime('%Y%m%d') if date_from is not None else "NoStartDate"
                end_date = date_to.strftime('%Y%m%d') if date_to is not None else "NoEndDate"
            else:
                if date_from is None: 
                    start_date = costs_df['date'].min().strftime('%Y%m%d')
                else:
                    start_date = date_from.strftime('%Y%m%d')

                if date_to is None:
                    end_date = costs_df['date'].max().strftime('%Y%m%d')
                else:
                    end_date = date_to.strftime('%Y%m%d')

            # Save results
            filename = f"{client}_{start_date}_{end_date}.xlsx"
            self.storage_manager.to_excel(costs_df, filename, client=client)
            self.logger.info(f"Batch cost saved to {filename}")
            
            # Print summary
            total_cost = costs_df['cost'].sum()
            self.logger.info(f"Total cost for the period: ${total_cost:.2f}")
            
            return costs_df
        
        except ValueError as e:
            msg = f"Calculate_api_costs, a value error occurred: {str(e)}"
            self.handle_error(self.logger, logging.ERROR, msg)
        except Exception as e:
            msg = f"Calculate_api_costs, an unknown error occurred: {str(e)}"
            self.handle_error(self.logger, logging.ERROR, msg)
        
        return None


    async def run(self):
        """
        Main execution method for the WebResearchApp.

        This method orchestrates the entire process of loading pricing data,
        creating client managers, processing clients, and calculating API costs.

        The method performs the following steps:
        1. Loads pricing data for API usage.
        2. Checks the sequentiality of pricing data.
        3. Creates client managers for each client.
        4. Processes all clients asynchronously.
        5. Calculates and saves API costs for each client.

        Any critical errors during execution are logged and handled.

        Returns:
            None
        """
        try:
            # Load pricing data
            self.load_pricing_data(self.config['API_PRICING_FILENAME'])
            self.check_pricing_sequentiality()
            # print("etablished pricing")

            # Create client managers
            # print("subscriptions filename is: ", self.config['SUBSCRIPTIONS_FILENAME'])
            self.create_client_managers(self.config['SUBSCRIPTIONS_FILENAME'])
            # print(""etablished client managers: {self.client_managers}")

            # Process clients asynchronously
            for client_manager in self.client_managers:
                # print("starting processing")
                await client_manager.process_client()

            # Calculate and save API costs for each client
            for client_manager in self.client_managers:
                consumption_filename = self.config['DF_CONSUMPTION_FILENAME']
                self.calculate_api_costs(
                    consumption_filename=consumption_filename,
                    client=client_manager.config['CLIENT']
                )

            # maintain list of blog URL's

        except Exception as e:
            self.handle_error(self.logger, logging.CRITICAL, f"Error in main application run: {str(e)}")


def run_app():
    # Load environment variables from .env file
    load_dotenv()
    app = WebResearchApp()
    asyncio.run(app.run())

if __name__ == "__main__":
    # print("Attempting to run the application:")
    run_app()
