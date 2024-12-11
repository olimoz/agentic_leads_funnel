import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional

from agents.perplexity_agent import PerplexityAgent
from agents.tavily_agent import TavilyAgent
from agents.search_proposal import SearchProposalAgent
from agents.url_extraction import URLextractionAgent
from agents.target_score import TargetScoreAgent
from agents.results_comparison import ResultsComparisonAgent
from agents.base import AgentBase

#======================================================================================
# CANDIDATE PIPELINE
#======================================================================================

class CandidatePipeline:
    """
    Manages the pipeline for processing candidates, including search operations and result analysis.
    """
    def __init__(self, app, config, llm, llm_advanced):
        """
        Initialize the CandidatePipeline.

        Args:
            app (WebResearchApp): The main application instance.
            config (Dict[str, Any]): Configuration dictionary.
            llm (Any): Language model instance.
        """
        self.app = app
        self.config = config
        self.llm = llm
        self.llm_advanced = llm_advanced
        self.perplexity_agent = PerplexityAgent(app)
        self.tavily_agent = TavilyAgent(app)
        self.search_proposal_agent = SearchProposalAgent(app)
        self.extract_urls_agent = URLextractionAgent(app)
        self.target_score_agent = TargetScoreAgent(app)
        self.results_comparison_agent = ResultsComparisonAgent(app)

    async def process(self, candidate, client, semaphore,
                      search_limiter_perplexity, search_limiter_tavily):
        """
        Process a candidate through the LLM agent pipeline (searches and emails)

        Args:
            candidate (Candidate): The candidate to process.
            client (str): The client identifier.
            semaphore (asyncio.Semaphore): Semaphore for concurrency control.
            search_limiter_perplexity (AsyncLimiter): Rate limiter for Perplexity searches.
            search_limiter_tavily (AsyncLimiter): Rate limiter for Tavily searches.

        Returns:
            Tuple[CandidateSearch, List[Dict[str, Any]]]: The processed candidate search and consumption data.
        """
        async with semaphore:
            consumption_row = []

            # log progress
            msg = f"- Processing: {candidate.first_name} {candidate.last_name}, {candidate.company}"
            print(msg)
            self.app.logger.info(msg)

            # Get or create a new CandidateSearch
            candidate_search = candidate.get_latest_search()
            if not candidate_search :
                candidate_search = candidate.add_search(datetime.now(), "", "", "", "", "", "", "")

            # Create search_period relative to previous search date
            search_period = candidate_search.get_search_period()

            # Get search event type
            search_event_type, consumption = await self.get_search_event_type(candidate, search_limiter_perplexity)
            consumption_row.append(consumption)
            candidate_search.search_event_type = search_event_type

            # Get Search Queries from agent
            search_queries, consumption = await self.get_search_queries(candidate, client, search_event_type, search_period)
            consumption_row.append(consumption)
            
            # append the standard query "fred bloggs at ACME ltd offical blog or case studies"
            agent_base = AgentBase(self.app)
            standard_query_template = agent_base.prompt_from_file(f"{client}/prompt_standardquery.txt", client=None)
            standard_query = standard_query_template.format(candidate=candidate, search_period=search_period)
            search_queries.append(standard_query)

            # record list of all queries
            candidate_search.search_query = "\n===\n".join(search_queries)

            # Perform searches
            search_results_list, consumption_list = await self.perform_searches(search_queries, search_limiter_perplexity, search_limiter_tavily)
            for consumption in consumption_list:
                consumption_row.append(consumption)
            search_raw = "/n===/n".join(search_results_list)
            candidate_search.search_raw = search_raw

            # Extract URL's for LinkedIn, Facebook and Company URL
            url_facebook, url_linkedin, url_company, consumption = await self.extract_urls(candidate, search_raw, client)
            consumption_row.append(consumption)
            candidate_search.url_facebook = url_facebook
            candidate_search.url_linkedin = url_linkedin
            candidate_search.url_company  = url_company
            
            # Get activity scores
            activity_score, services_need_score, priority_reasoning, consumption = await self.get_activity_scores(search_raw, candidate, search_period, client)
            consumption_row.append(consumption)
            candidate_search.search_results = priority_reasoning

            # Get novelty score
            previous_search = candidate.get_previous_search(candidate_search)
            novelty_score, novelty_reasoning, consumption = await self.get_novelty_score(candidate, client, search_raw, 
                                                                                         previous_search.search_results if previous_search else "")
            consumption_row.append(consumption)
            candidate_search.novelty_score = novelty_score

            # Calculate total scores
            candidate_search.set_search_scores(novelty_score, activity_score, services_need_score)

            # log progress
            msg = f"Finished Processing: {candidate.first_name} {candidate.last_name}, {candidate.company}"
            self.app.logger.info(msg)

            return candidate_search, consumption_row

    async def get_search_event_type(self, candidate, search_limiter_perplexity):
        """
        Get the search event type which is specific to a candidate and their industry, so we can search for such events

        Args:
            candidate (Candidate): The candidate to get the search event type for.
            search_limiter_perplexity (AsyncLimiter): Rate limiter for Perplexity searches.

        Returns:
            Tuple[str, Dict[str, Any]]: The search event type and consumption data.
        """
        async with search_limiter_perplexity:
            query = f"""What kind of events, blogs and updates are typically published by {candidate.first_name} {candidate.last_name}, 
            who works as {candidate.position} at this company: {candidate.company}. Ignore similar named companies and people. Focus on this one only."""
            return await self.perplexity_agent.run(query)

    async def get_search_queries(self, candidate, client, search_event_type, search_period):
        """
        Generate search queries for a candidate, what precisely are we asking the search engine for?

        Args:
            candidate (Candidate): The candidate to generate queries for.
            client (str): The client identifier.
            search_event_type (str): The type of search event.
            search_period (str): The search period.

        Returns:
            Tuple[List[str], Dict[str, Any]]: The generated search queries and consumption data.
        """
        params = {
            'search_event_type': search_event_type,
            'search_query_qty': self.config['MAX_PPLX_SEARCHES'],
            'search_period': search_period,
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'company': candidate.company,
            'search_sites_list': ['']
        }
        return await self.search_proposal_agent.run(self.llm, params, client)

    async def perform_searches(self, search_queries, search_limiter_perplexity, search_limiter_tavily):
        """
        Perform internet searches (Perplexity and Tavily)using the generated queries.

        Args:
            search_queries (List[str]): The list of search queries to perform.
            search_limiter_perplexity (AsyncLimiter): Rate limiter for Perplexity searches.
            search_limiter_tavily (AsyncLimiter): Rate limiter for Tavily searches.

        Returns:
            Tuple[List[str], List[Dict[str, Any]]]: The search results and consumption data.
        """
        search_results_list = []
        consumption_list = []

        # Perplexity searches
        for search_query in search_queries:
            async with search_limiter_perplexity:
                result, consumption = await self.perplexity_agent.run(search_query)
                search_results_list.append(result)
                consumption_list.append(consumption)

        # Tavily search (first query only)
        if self.config['MAX_TAVILY_SEARCHES'] > 0:
            async with search_limiter_tavily:
                result, consumption = await self.tavily_agent.run(search_queries[0], self.config)
                search_results_list.append(self.tavily_agent.tavily_result_to_text(result))
                consumption_list.append(consumption)

        return search_results_list, consumption_list

    async def extract_urls(self, candidate, search_raw, client):
        """
        Multiple searches, Tavily and Perplexity, are produced. We need to extract the urls relevant to the search candidate.

        Args:
            candidate (Candidate): The candidate whose results are being merged.
            client (str): The client identifier.
            search_results (str): The raw search results

        Returns:
            Tuple[str, Dict[str, Any]]: The merged results and consumption data.
        """
        params = {
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'company': candidate.company,
            'search_raw': search_raw
        }

        return await self.extract_urls_agent.run(self.llm, params, client)

    async def get_activity_scores(self, search_raw, candidate, search_period, client):
        """
        Get activity scores based on the search results. The more relevant news in the period, the more active we score the candidate

        Args:
            search_results (str): The merged search results.
            client (str): The client identifier.

        Returns:
            Tuple[int, int, str, Dict[str, Any]]: Activity score, services need score, reasoning, and consumption data.
        """
        params = {
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'company': candidate.company,
            'search_period': search_period,
            'details': search_raw,
        }

        return await self.target_score_agent.run(self.llm_advanced, params, client)

    async def get_novelty_score(self, candidate, client, search_results, previous_results):
        """
        Get the novelty score (how new is the news??) by comparing current and previous search results.

        Args:
            candidate (Candidate): The candidate being evaluated.
            client (str): The client identifier.
            search_results (str): The current search results.
            previous_results (str): The previous search results.

        Returns:
            Tuple[int, str, Dict[str, Any]]: Novelty score, reasoning, and consumption data.
        """
        params = {
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'company': candidate.company,
            'search_results': search_results,
            'search_results_previous': previous_results
        }
        return await self.results_comparison_agent.run(self.llm, params, client)