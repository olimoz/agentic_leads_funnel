"""Agent responsible for analyzing business activity and services needs."""

from agents.base import AgentBase
from langchain_core.prompts import ChatPromptTemplate
import os
import json
import logging

class TargetScoreAgent(AgentBase):
    """
    Agent responsible for analyzing business activity and services needs.
    """
    async def run(self, llm, params, client):
        """
        Analyze business activity and services needs based on provided text.

        Args:
            llm: The language model to use for scoring.
            params (str): A string describing the business's recent activities.
            client (str): The client identifier.

        Returns:
            tuple: Activity score, services need score, reasoning, and consumption details.
        """
        try:

            # Define the prompt template
            prompt_text = self.prompt_from_file('prompt_targetscoreagent.txt', client=client)

            # Define tools for scoring
            tools = [{
                "name": "score_business",
                "description": "Score of business text for services production need, as per metrics",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reasoning": {
                            "type": "string",
                            "description": "Explanation for the score given the metrics"
                        },                        
                        "services_need_score": {
                            "type": "integer",
                            "description": "Score of the text to inform services production needs, as per metrics (0-10)"
                        },
                        "summary_of_facts": {
                            "type": "string",
                            "description": "List of facts in the text which led to the score, not mentioning metrics"
                        }
                    },
                    "required": ["reasoning", "services_need_score", "summary_of_facts"]
                }
            }]

            # Create the prompt using ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You score results of web searches according to a strict set of metrics"),
                ("human", prompt_text),
            ]).partial()

            # Create the chain to invoke the language model
            prompt_input = {
                'first_name': lambda x: x['first_name'],
                'last_name': lambda x: x['last_name'],
                'company': lambda x: x['company'],
                'search_period': lambda x: x['search_period'],
                'details': lambda x: x['details']
            }

            # Create the chain to invoke the language model
            chain = (prompt_input | prompt | llm.bind_tools(tools, tool_choice="score_business"))


            # Debug
            # print(f"prompt_input: {prompt_input}")

            # Invoke the chain asynchronously
            response = await chain.ainvoke(params)

            # Extract function arguments from the response
            func_args = response.additional_kwargs['tool_calls'][0]['function']['arguments']

            # Extract the scores from the JSON response
            try:
                func_args_data = json.loads(func_args)
                activity_score = 0 #int(func_args_data['activity_score'])
                services_need_score = int(func_args_data['services_need_score'])
                reasoning = func_args_data['reasoning']
                summary = func_args_data['summary_of_facts']

            except json.JSONDecodeError:
                msg = "Results_Merging_agent, Error: Invalid JSON"
                await self.app.handle_error(self.app.logger, logging.ERROR, msg)
            except KeyError as e:
                msg = f"Results_Merging_Agent, Error: Missing key in JSON: {str(e)}"
                await self.app.handle_error(self.app.logger, logging.ERROR, msg)

            # Log the consumption
            consumption = await self.log_consumption(
                function_name='target_score_agent',
                model=response.response_metadata['model_name'],
                search_calls=0,
                input_tokens=response.response_metadata['token_usage']['prompt_tokens'],
                output_tokens=response.response_metadata['token_usage']['completion_tokens']
            )

            # Return the extracted scores and summary. 
            # Reasoning is deprecated, used only to assist LLM reach the score.
            return activity_score, services_need_score, summary, consumption

        except Exception as e:
            msg = f"target_score_agent, An error occurred while executing: {str(e)}"
            await self.app.handle_error(self.app.logger, logging.ERROR, msg)
            return 0, 0, "", {
                'function': 'target_score_agent',
                'model': 'unknown',
                'search_calls': 0,
                'input_tokens': 0,
                'output_tokens': 0
            }
