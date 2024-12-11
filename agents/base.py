"""Base class for all agent implementations."""

#======================================================================================
# Agent Classes
#======================================================================================

class AgentBase:
    """
    Base class for all agent implementations.

    This class provides common functionality for logging consumption
    and loading prompts from files with caching.
    """
    def __init__(self, app):
        """
        Initialize the AgentBase.

        Args:
            app: The main application instance.
        """
        self.app = app
        self.prompt_cache = {}
        self.storage_manager = app.storage_manager

    async def log_consumption(self, function_name, model, search_calls, input_tokens, output_tokens):
        """
        Log the LLM's consumption (i.e. tokens, searches) for the agent.

        Args:
            function_name (str): Name of the function being logged.
            model (str): Name of the model used.
            search_calls (int): Number of search calls made.
            input_tokens (int): Number of input tokens used.
            output_tokens (int): Number of output tokens generated.

        Returns:
            dict: A dictionary containing the consumption details.
        """
        consumption = {
            'function': function_name,
            'model': model,
            'search_calls': search_calls,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens
        }
        # self.app.logger.info(f"Consumption: {consumption}")
        return consumption

    def prompt_from_file(self, file_path, client=None):
        """
        Load a prompt from a file, with caching for faster execution.

        This method uses the StorageManager to read files, supporting both local
        and cloud storage environments. It also implements caching to improve
        performance for frequently accessed prompts.

        Args:
            file_path (str): Path to the file containing the prompt.
            client (str, optional): The client name, used as a subfolder or blob prefix.

        Returns:
            str: The content of the prompt file, or None if an error occurs.
        """
        cache_key = f"{client}:{file_path}" if client else file_path
        
        if cache_key not in self.prompt_cache:
            try:
                content = self.storage_manager.read_file(file_path, client=client)
                self.prompt_cache[cache_key] = content
            except Exception as e:
                msg = f"prompt_from_file, {self.__class__.__name__}: error reading file {file_path}: {str(e)}"
                self.app.handle_error(self.app.logger, logging.CRITICAL, msg)
                return None
        
        return self.prompt_cache.get(cache_key)