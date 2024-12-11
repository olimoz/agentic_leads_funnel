"""Agent for performing searches using the Perplexity API."""

from langchain_community.chat_models import ChatPerplexity
from langchain_core.prompts import ChatPromptTemplate
from agents.base import AgentBase
import ast
import logging

class PerplexityAgent(AgentBase):
    """
    Agent for performing searches using the Perplexity API.
    """
    from tenacity import retry, stop_after_attempt, wait_random_exponential  # for exponential backoff
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def run(self, search_query, temperature=0):
        """
        Execute a search using the Perplexity API.

        Args:
            search_query (str): The query to search for.
            temperature (float, optional): The temperature for the language model. Defaults to 0.

        Returns:
            tuple: A tuple containing the search response content and consumption details.
        """
        try:
            model_name = "llama-3.1-sonar-small-128k-online"
            ppx = ChatPerplexity(temperature=temperature, model=model_name)
            prompt = ChatPromptTemplate.from_messages([("system", "You are a helpful assistant with access to the internet."), 
                                                       ("human", "{input}")])
            chain = prompt | ppx
            response = await chain.ainvoke({"input": search_query})
            
            #citations = response.model_extra.get("citations")
            
            # Extract content
            def response_extraction(item, use_string):
                if isinstance(response, dict) and item in response:
                    item_value = response[item]
                elif hasattr(response, item):
                    item_value = getattr(response, item)
                elif use_string: 
                    item_value = str(response)
                else:
                    item_value = '[]'
                return item_value

            content   = response_extraction('content', use_string=True)
            citations = response_extraction('citations', use_string=False)

            if type(citations) == str:
                citations = ast.literal_eval(citations)

            if type(citations) == list:
                citation_text = ""
                for index, url in enumerate(citations, start=1):
                    citation = f"{index}, {url}\n"
                    citation_text = citation_text+citation

                content = content + "\n\n" + citation_text

            # Log consumption
            consumption = await self.log_consumption(
                function_name="perplexity_tool",
                model=model_name,
                search_calls=1,
                input_tokens=ppx.get_num_tokens(search_query),
                output_tokens=ppx.get_num_tokens(content)
            )

            return content, consumption

        except Exception as e:
            msg = f"An error occurred while executing perplexity_tool: {str(e)}"
            await self.app.handle_error(self.app.logger, logging.ERROR, msg)
            return "", {
                'function': 'perplexity_tool',
                'model': 'perplexity_' + model_name,
                'search_calls': 0,
                'input_tokens': 0,
                'output_tokens': 0,
                'error': str(e)
            }
