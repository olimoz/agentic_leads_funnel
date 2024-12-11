"""Agent for generating email proposals based on search results."""

from agents.base import AgentBase
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence

class EmailProposalAgent(AgentBase):
    """Agent for generating email proposals based on search results."""

    async def run(self, llm, first_name, last_name, company, search_results, client):
        """
        Generate an email proposal based on search results and business information.

        Args:
            llm: The language model to use for email generation.
            first_name (str): The first name of the target individual.
            last_name (str): The last name of the target individual.
            company (str): The company of the target individual.
            search_results (str): The search results for the individual.
            client (str): The name of the client.

        Returns:
            Tuple[str, Dict[str, Any]]: A tuple containing:
                - email_content (str): The generated email content.
                - consumption (Dict[str, Any]): Details of resource consumption.
        """
        business_description = self.prompt_from_file(f"{client}/{self.app.config['BUSINESS_DESCRIPTION_FILENAME']}")
        email_template = self.prompt_from_file(f"{client}/{self.app.config['EMAIL_TEMPLATE_FILENAME']}")
        prompt_text = self.prompt_from_file(f"{client}/prompt_emailproposalagent.txt")

        prompt = ChatPromptTemplate.from_template(prompt_text)
        chain = RunnableSequence(prompt, llm)

        prompt_params = {
            'search_name_first': first_name,
            'search_name_last': last_name,
            'search_company': company,   
            'search_results': search_results,
            'email_template': email_template,
            'business_description': business_description
        }

        response = await chain.ainvoke(prompt_params)

        consumption = await self.log_consumption(
            function_name='email_proposal_agent',
            model=response.response_metadata['model_name'],
            search_calls=0,
            input_tokens=response.response_metadata['token_usage']['prompt_tokens'],
            output_tokens=response.response_metadata['token_usage']['completion_tokens']
        )

        return response.content, consumption