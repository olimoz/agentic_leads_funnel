"""
URL Extraction Agent for extracting relevant URLs from search results.
"""

import os
import json
import logging
from typing import Dict, Any, Tuple
from langchain.prompts import ChatPromptTemplate
from agents.base import AgentBase

class URLextractionAgent(AgentBase):
    """
    Agent responsible for merging and processing search results.
    """
    async def run(self, llm, params, client):
        """
        Merge and process search results for a given query and extract relevant information.
        
        Args:
            llm: The language model to use for processing.
            search_query (str): The query that generated the search results.
            first_name (str): The first name of the person to extract information about.
            last_name (str): The last name of the person to extract information about.
            company (str): The company associated with the person.
            search_results_list (list): A list of search result strings to be merged and analyzed.
            client (str): The client identifier.

        Returns:
            tuple: Extracted content and consumption details.
        """
        # establish defaults
        url_facebook = ""
        url_linkedin = ""
        url_company  = ""

        tools = [{
                "name": "extract_urls",
                "description": "Extracts Facebook, LinkedIn and company URLs from a text.",
                "parameters": {
                    "type": "object",
                    "properties": {
                    "url_facebook": {
                        "type": "string",
                        "description": "The Facebook profile URL of the organization.",
                        "example": "https://www.facebook.com/anicca"
                    },
                    "url_linkedin": {
                        "type": "string",
                        "description": "The LinkedIn profile URL of the individual.",
                        "example": "https://www.linkedin.com/in/annstanley"
                    },
                    "url_company": {
                        "type": "string",
                        "description": "The company website URL.",
                        "example": "https://www.anicca.co.uk"
                    }
                    },
                    "required": ["url_facebook", "url_linkedin", "url_company"]
                }
                }]

        try:
            # Define the prompt template
            prompt_text = self.prompt_from_file('prompt_urlextractionagent.txt', client=client)

            # Create the prompt using ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You extract company and personal urls from urls in a text."),
                ("human", prompt_text),
            ]).partial()

            prompt_input = {
                'first_name': lambda x: x['first_name'],
                'last_name': lambda x: x['last_name'],
                'company': lambda x: x['company'],
                'search_raw': lambda x: x['search_raw']
            }

            # Create the chain to invoke the language model
            chain = (prompt_input | prompt | llm.bind_tools(tools, tool_choice="extract_urls"))

            # Invoke the chain asynchronously
            response = await chain.ainvoke(params)

            # Extract function arguments from the response
            func_args = response.additional_kwargs['tool_calls'][0]['function']['arguments']

            # Extract the scores from the JSON response
            try:

                # Test if the response is a string that needs to be evaluated as a JSON object
                func_args_data = json.loads(func_args) if isinstance(func_args, str) else func_args

                url_facebook = func_args_data['url_facebook']
                url_linkedin = func_args_data['url_linkedin']
                url_company  = func_args_data['url_company']

            except json.JSONDecodeError:
                msg = "URLextractionAgent, Error: Invalid JSON string received."
                self.app.handle_error(self.app.logger, logging.ERROR, msg)

            except KeyError as e:
                msg = f"URLextractionAgent, Error: Missing key in JSON: {str(e)}"
                self.app.handle_error(self.app.logger, logging.ERROR, msg)

            # Log the consumption
            consumption = await self.log_consumption(
                function_name='URLextractionAgent',
                model=response.response_metadata['model_name'],
                search_calls=0,
                input_tokens=response.response_metadata['token_usage']['prompt_tokens'],
                output_tokens=response.response_metadata['token_usage']['completion_tokens']
            )
            # Return the extracted scores and summary. 
            # Reasoning is deprecated, used only to assist LLM reach the score.
            return url_facebook, url_linkedin, url_company, consumption

        except Exception as e:
            msg = f"Results_merging_agent error: {str(e)}"
            self.app.handle_error(self.app.logger, logging.ERROR, msg)
            return url_facebook, url_linkedin, url_company, {
                'function': 'results_merging_agent',
                'model': 'unknown',
                'search_calls': 0,
                'input_tokens': 0,
                'output_tokens': 0
            }