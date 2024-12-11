"""Agent for performing searches using the Brave Search API."""

from langchain_community.tools import BraveSearch
from agents.base import AgentBase
import logging

class BraveAgent(AgentBase):
    """
    Agent for performing searches using the Brave Search API.
    """
    async def run(self, search_query, config):
        """
        Execute a search using the Brave search tool and return the results along with consumption details.
        
        Args:
            search_query (str): The query to search for.
            config (dict): Configuration containing API key and max searches.
        Returns:
            tuple: A tuple containing the search response and consumption details.
        """
        try:
            # Create the Brave search tool instance
            search_tool = BraveSearch.from_api_key(
                api_key=config['BRAVE_API_KEY'], 
                search_kwargs={"count": config['MAX_BRAVE_SEARCHES']}
            )

            # Execute the search asynchronously using asyncio.to_thread
            response_str = await asyncio.to_thread(search_tool.run, search_query)

            # Convert the response from string to list using ast.literal_eval for safety
            response = ast.literal_eval(response_str)

            # Ensure the response is a list
            if not isinstance(response, list):
                raise ValueError("Unexpected response format from Brave search")

            # Log the consumption
            consumption = await self.log_consumption(
                function_name='brave_tool',
                model='Brave',
                search_calls=len(response),
                input_tokens=0,  # Brave doesn't track token usage
                output_tokens=0
            )

            return response, consumption

        except Exception as e:
            msg = f"An error occurred while executing brave_tool: {str(e)}"
            await self.app.handle_error(self.app.logger, logging.ERROR, msg)
            return [], {
                'function': 'brave_tool',
                'model': 'Brave',
                'search_calls': 0,
                'input_tokens': 0,
                'output_tokens': 0
            }
