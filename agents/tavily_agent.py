"""Agent for performing searches using the Tavily API."""

from langchain_community.tools.tavily_search import TavilySearchResults
from agents.base import AgentBase
import asyncio
import logging

class TavilyAgent(AgentBase):
    """
    Agent for performing searches using the Tavily API.
    """

    async def run(self, search_query, config, **kwargs):
        """
        Execute a search using the Tavily search tool and return the results along with consumption details.
        
        Args:
            search_query (str): The query to search for.
            config (dict): Configuration containing max searches and other settings.
            **kwargs: Additional parameters passed to the Tavily search tool.

        Returns:
            tuple: A tuple containing the search response and consumption details.
        """
        try:
            # Create Tavily search tool instance
            search_tool = TavilySearchResults(max_results=config['MAX_TAVILY_SEARCHES'], include_images=False)
            
            # Execute the search asynchronously
            response = await asyncio.to_thread(search_tool, search_query, **kwargs)

            # Log the consumption
            consumption = await self.log_consumption(
                function_name='tavily_tool',
                model='tavily',
                search_calls=len(response),
                input_tokens=0,  # Tavily doesn't track token usage
                output_tokens=0
            )

            return response, consumption

        except Exception as e:
            msg = f"An error occurred while executing tavily_tool: {str(e)}"
            await self.app.handle_error(self.app.logger, logging.ERROR, msg)
            return [], {
                'function': 'tavily_tool',
                'model': 'tavily',
                'search_calls': 0,
                'input_tokens': 0,
                'output_tokens': 0
            }

    def tavily_result_to_text(self, dict_list):
        """
        Convert Tavily search results from a list of dictionaries to a formatted string.

        Args:
            dict_list (list): A list of dictionaries containing Tavily search results.
        Returns:
            str: A formatted string representation of the search results.
        """
        # Check if input is valid
        if not isinstance(dict_list, list) or not dict_list:
            return "No search results available."
        
        formatted_text = ""
        valid_results = False
        
        try:
            for item in dict_list:
                if isinstance(item, dict) and 'url' in item and 'content' in item:
                    formatted_text += f"URL: {item['url']}\n"
                    formatted_text += f"Content: {item['content']}\n"
                    formatted_text += "-" * 50 + "\n"
                    valid_results = True
            
            return formatted_text if valid_results else "No search results available."
        except:
            return "No search results available."