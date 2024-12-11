"""Agent for comparing search results and scoring novelty."""

from agents.base import AgentBase
from langchain_core.prompts import ChatPromptTemplate
import logging
import json
import os

class ResultsComparisonAgent(AgentBase):
    """Agent for comparing search results and scoring novelty."""

    async def run(self, llm, params, client):
        """
        Compare two sets of search results and score the novelty based on differences.
        Used to understand whether anything new has been published about the individual or company recently.

        Args:
            llm: The language model to use for scoring.
            params (dict): A dictionary containing:
                - first_name (str): The first name of the individual.
                - last_name (str): The last name of the individual.
                - company (str): The company associated with the individual.
                - search_results (str): The recent search results.
                - search_results_previous (str): The previous search results.
            client (str): The name of the client.

        Returns:
            Tuple[int, str, Dict[str, Any]]: A tuple containing:
                - novelty_score (int): The novelty score (1-10).
                - reasoning (str): Explanation for the score given.
                - consumption (Dict[str, Any]): Details of resource consumption.
        """
        try:
            # Define the tool for scoring novelty
            tools = [{
                "name": "results_novelty_score",
                "description": "Score novelty of recent search results vs previous results",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "novelty_score": {
                            "type": "integer",
                            "description": "Score of how novel the new search results are (1-10)"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Explanation for the score given"
                        }
                    },
                    "required": ["novelty_score", "reasoning"]
                }
            }]

            # Define the prompt template
            prompt_text = self.prompt_from_file(os.path.join(client,'prompt_resultscomparisonagent.txt'))

            # Create the prompt using ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a web researcher."),
                ("human", prompt_text),
            ]).partial()

            # Create the chain to invoke the language model
            prompt_input = {
                'first_name': lambda x: x['first_name'],
                'last_name': lambda x: x['last_name'],
                'company': lambda x: x['company'],
                'search_results': lambda x: x['search_results'],
                'search_results_previous': lambda x: x['search_results_previous']
            }
            chain = (prompt_input | prompt | llm.bind_tools(tools, tool_choice="results_novelty_score"))

            # Invoke the chain asynchronously
            response = await chain.ainvoke(params)

            # Extract function arguments from the response
            func_args = response.additional_kwargs['tool_calls'][0]['function']['arguments']

            # Extract the novelty score and reasoning from the JSON response
            try:
                func_args_data = json.loads(func_args)
                novelty_score = int(func_args_data['novelty_score'])
                reasoning = func_args_data['reasoning']
            except json.JSONDecodeError:
                msg = "Results_Comparison_Agent: Error: Invalid JSON"
                await self.app.handle_error(self.app.logger, logging.ERROR, msg)
                novelty_score, reasoning = -1, "Error: Invalid JSON"
            except KeyError as e:
                msg = f"Results_Comparison_Agent: Error: Missing key in JSON: {str(e)}"
                await self.app.handle_error(self.app.logger, logging.ERROR, msg)
                novelty_score, reasoning = -1, f"Error: Missing key in JSON: {str(e)}"

            # Log the consumption
            consumption = await self.log_consumption(
                function_name='results_comparison_agent',
                model=response.response_metadata['model_name'],
                search_calls=0,
                input_tokens=response.response_metadata['token_usage']['prompt_tokens'],
                output_tokens=response.response_metadata['token_usage']['completion_tokens']
            )

            # Return the novelty score, reasoning, and consumption
            return novelty_score, reasoning, consumption

        except Exception as e:
            msg = f"An error occurred while executing results_comparison_agent: {str(e)}"
            await self.app.handle_error(self.app.logger, logging.ERROR, msg)
            return -1, "Error occurred during execution", {
                'function': 'results_comparison_agent',
                'model': 'unknown',
                'search_calls': 0,
                'input_tokens': 0,
                'output_tokens': 0
            }
