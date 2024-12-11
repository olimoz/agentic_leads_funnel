"""Agent responsible for generating search queries."""

import os
import json
import logging
from agents.base import AgentBase
from langchain_core.prompts import ChatPromptTemplate

class SearchProposalAgent(AgentBase):
    """
    Agent responsible for generating search queries based on given parameters.
    """
    async def run(self, llm, params, client):
        """
        Generate search queries based on the provided parameters.

        Args:
            llm: The language model to use for query generation.
            params (dict): Parameters for query generation, including search event type, period, and candidate info.
            client (str): The client identifier.

        Returns:
            tuple: A list of generated search queries and consumption details.
        """
        try:
            tools = [{
                "name": "submit_search_queries",
                "description": "Submit multiple search queries",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_queries": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of search queries to be submitted"
                        }
                    },
                    "required": ["search_queries"]
                }
            }]
            
            prompt_input = {
                'search_event_type': lambda x: x['search_event_type'],
                'search_period': lambda x: x['search_period'],
                'search_query_qty': lambda x: x['search_query_qty'],
                'first_name': lambda x: x['first_name'],
                'last_name': lambda x: x['last_name'],
                'company': lambda x: x['company'],
                'search_sites_string': lambda x: ", ".join(x['search_sites_list'])
            }

            prompt_text = self.prompt_from_file('prompt_searchproposalagent.txt', client=client)

            # Create the prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a web research planner."),
                ("human", prompt_text),
            ]).partial()

            # Create the chain
            chain = (prompt_input | prompt | llm.bind_tools(tools, tool_choice="submit_search_queries"))

            # Invoke the chain
            response = await chain.ainvoke(params)

            # Extract search queries
            func_args = response.additional_kwargs['tool_calls'][0]['function']['arguments']
            func_args_data = json.loads(func_args)
            search_queries = func_args_data['search_queries']
            # print(f"search queries: {search_queries}")
            # Log consumption
            consumption = await self.log_consumption(
                function_name="search_proposal_agent",
                model=response.response_metadata['model_name'],
                search_calls=0,
                input_tokens=response.response_metadata['token_usage']['prompt_tokens'],
                output_tokens=response.response_metadata['token_usage']['completion_tokens']
            )

            return search_queries, consumption

        except json.JSONDecodeError as e:
            msg = f"Search Proposal Agent, Error: Invalid JSON: {str(e)}"
            await self.app.handle_error(self.app.logger, logging.ERROR, msg)

        except KeyError as e:
            msg = f"Search Proposal Agent, Error: Missing key in JSON: {str(e)}"
            await self.app.handle_error(self.app.logger, logging.ERROR, msg)
