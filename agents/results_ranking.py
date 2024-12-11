from agents.base import AgentBase
import os
import logging
import json
from langchain.prompts import ChatPromptTemplate

class SearchResultsRankingAgent(AgentBase):
    """
    Agent responsible for analyzing business activity and service needs.
    """

    async def run(self, llm, texts, client):
        """
        Rank search results by their potential for services.

        Args:
            llm: The language model to use for scoring.
            texts (str): A string describing the business's recent activities.
            client (str): The client identifier.

        Returns:
            tuple: List of dicts; ranking, id, reasoning. Also returns consumption details.
        """
        try:

            # Define the prompt template
            prompt_text = self.prompt_from_file('prompt_searchresultsrankingagent.txt', client=client)

            # Define tools for scoring
            tools = [{
                "name": "rank_potential",
                "description": "Rank multiple business texts by their potential for services need. Each entry contains first name, last name, company, and rank.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "rankings": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "first_name": {
                                        "type": "string",
                                        "description": "First name of the individual"
                                    },
                                    "last_name": {
                                        "type": "string",
                                        "description": "Last name of the individual"
                                    },
                                    "company": {
                                        "type": "string",
                                        "description": "Company associated with the individual"
                                    },
                                    "rank": {
                                        "type": "integer",
                                        "description": "Rank of the text to inform business service needs (1-10)"
                                    }
                                },
                                "required": ["first_name", "last_name", "company", "rank"],
                                "description": "A dictionary containing first name, last name, company, and rank"
                            },
                            "description": "List of dictionaries, each containing first name, last name, company, and rank"
                        },
                    },
                    "required": ["rankings"]
                }
            }]


            # Create the prompt using ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You rank texts for their potential for the provision of services."),
                ("human", prompt_text),
            ]).partial()

            # Create the chain to invoke the language model
            prompt_input = {
                'texts': texts
            }
            chain = (prompt | llm.bind_tools(tools, tool_choice="rank_potential"))

            # Invoke the chain asynchronously
            response = await chain.ainvoke(prompt_input)

            # Extract function arguments from the response
            func_args = response.additional_kwargs['tool_calls'][0]['function']['arguments']

            # Extract the scores from the JSON response
            try:

                # Test if the response is a string that needs to be evaluated as a JSON object
                if isinstance(func_args, str):
                    # Attempt to parse the string as a JSON object
                    try:
                        func_args_data = json.loads(func_args)
                        # Successfully parsed, func_args_data is now a Python object (likely a dict or list of dicts)
                        rankings = func_args_data.get('rankings', [])
                    except json.JSONDecodeError:
                        # Handle invalid JSON error
                        msg = "SearchResultsRankingAgent, Error: Invalid JSON string received."
                        self.app.handle_error(self.app.logger, logging.ERROR, msg)
                        rankings = [{"first_name": "Unknown", "last_name":"Unknown", "company":"Unknown", "rank": -1}]
                else:
                    # If func_args is already a Python object (not a string), use it directly
                    rankings = func_args.get('rankings', [])

            except json.JSONDecodeError:
                msg = "SearchResultsRankingAgent, Error: Invalid JSON"
                await self.app.handle_error(self.app.logger, logging.ERROR, msg)
            except KeyError as e:
                msg = f"SearchResultsRankingAgent, Error: Missing key in JSON: {str(e)}"
                await self.app.handle_error(self.app.logger, logging.ERROR, msg)

            # Log the consumption
            consumption = await self.log_consumption(
                function_name='SearchResultsRankingAgent',
                model=response.response_metadata['model_name'],
                search_calls=0,
                input_tokens=response.response_metadata['token_usage']['prompt_tokens'],
                output_tokens=response.response_metadata['token_usage']['completion_tokens']
            )
            # Return the extracted scores and summary. 
            # Reasoning is deprecated, used only to assist LLM reach the score.
            return rankings, consumption

        except Exception as e:
            msg = f"SearchResultsRankingAgent, An error occurred while executing: {str(e)}"
            self.app.handle_error(self.app.logger, logging.ERROR, msg)
            return 0, 0, "", {
                'function': 'SearchResultsRankingAgent',
                'model': 'unknown',
                'search_calls': 0,
                'input_tokens': 0,
                'output_tokens': 0
            }