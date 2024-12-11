"""Classes for managing candidate information and searches."""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from typing import TYPE_CHECKING
from dateutil.relativedelta import relativedelta

if TYPE_CHECKING:
    from app import WebResearchApp

class Candidate:

    def __init__(self, app, first_name, last_name, company, position):
        """
        Initialize a Candidate object.
        
        Args:
            first_name (str): The candidate's first name
            last_name (str): The candidate's last name
            company (str): The candidate's company
            position (str): The candidate's position in the company
        """
        self.app = app
        self.first_name = first_name
        self.last_name = last_name
        self.company = company
        self.position = position
        self.searches = []

    def add_search(self, search_date, search_event_type, search_query, search_raw, url_facebook, url_linkedin, url_company,
                    search_results, novelty_score=None, activity_score=None, services_need_score=None, total_score=None):
        """
        Create and add a new search to the candidate's search history.
        
        Args:
            search_date (datetime): The date of the search
            search_event_type (str): The type of event searched for
            search_query (str): The query which led to the results
            search_raw (str): The raw results of the search (long text!)
            url_facebook (str): The URL to the candidate's Facebook page, taken from search_raw, if available
            url_linkedin (str): The URL to the candidate's LinkedIn page, taken from search_raw, if available
            url_company (str): The URL to the candidate's company page, taken from search_raw, if available
            search_results (str): The processed results of the search
            novelty_score (int, optional): The novelty score of the search results
            activity_score (int, optional): The activity score of the search results
            services_need_score (int, optional): The services need score of the search results
            total_score (int, optional): The total score of the search results

        Returns:
            CandidateSearch: The newly created CandidateSearch object
        """
        new_search = CandidateSearch(self, search_date, search_event_type, search_query, search_raw, url_facebook, url_linkedin, url_company,
                                    search_results, novelty_score, activity_score, services_need_score, total_score)
        self.searches.append(new_search)
        return new_search

    def get_latest_search(self):
        """
        Get the most recent search for the candidate.
        
        Returns:
            CandidateSearch: The most recent CandidateSearch object, or None if no searches exist
        """
        return max(self.searches, key=lambda s: s.search_date) if self.searches else None

    def get_previous_search(self, current_search):
        """
        Get the search results of the search immediately preceding the given search.
        
        Args:
            current_search (CandidateSearch): The current CandidateSearch object

        Returns:
            str: The search results of the previous search, or an empty string if there is no previous search
        """
        if not self.searches or current_search not in self.searches:
            return ""
        
        current_index = self.searches.index(current_search)
        if current_index > 0:
            return self.searches[current_index - 1].search_results
        return ""

    def is_eligible_for_processing(self):
        """
        Determine if the candidate is eligible for a new search based on the date of the last search.
        
        :return: True if eligible (no search in the last 30 days), False otherwise
        """
        latest_search = self.get_latest_search()
        if not latest_search:
            return True
        return (datetime.now() - latest_search.search_date).days > 30

    def to_dict(self):
        """
        Convert the candidate and their latest search data to a dictionary.
        
        :return: A dictionary containing the candidate's information and latest search data
        """
        data = {
            'First Name': self.first_name,
            'Last Name': self.last_name,
            'Company': self.company,
            #'Position': self.position
        }
        latest_search = self.get_latest_search()
        if latest_search:
            data.update(latest_search.to_dict())
        return data

    def __eq__(self, other):
        """
        Check if two Candidate objects are equal based on name and company.
        
        Args:
            other (object): Another object to compare with
        Returns:
            bool: True if the objects are equal, False otherwise
        """
        if not isinstance(other, Candidate):
            return NotImplemented
        return (self.first_name == other.first_name and
                self.last_name == other.last_name and
                self.company == other.company)

    def __hash__(self):
        """
        Generate a hash value for the Candidate object.
        
        :return: An integer hash value
        """
        return hash((self.first_name, self.last_name, self.company))


class CandidateSearch:

    def __init__(self, candidate, search_date, search_event_type, search_query, search_raw, url_facebook, url_linkedin, url_company,
                search_results, novelty_score=None, activity_score=None, services_need_score=None, total_score=None, priority_reasoning=None):
        """
        Initialize a CandidateSearch object.
        
        Args:
            candidate (Candidate): The Candidate object this search is associated with.
            search_date (datetime): The date of the search.
            search_event_type (str): The type of event searched for.
            search_query (str): The query which led to the results.
            search_raw (str): The raw results of the search (long text).
            url_facebook (str): The URL to the candidate's Facebook page, taken from search_raw, if available.
            url_linkedin (str): The URL to the candidate's LinkedIn page, taken from search_raw, if available.
            url_company (str): The URL to the candidate's company website, taken from search_raw, if available.
            search_results (str): The summarized results of the search.
            novelty_score (int, optional): The novelty score of the search results.
            activity_score (int, optional): The activity score of the search results.
            services_need_score (int, optional): The services need score of the search results.
            total_score (int, optional): The total score of the search results.
        """
        self.candidate = candidate
        self.search_date = search_date
        self.search_event_type = search_event_type
        self.search_query = search_query
        self.search_raw = search_raw
        self.url_facebook = url_facebook
        self.url_linkedin = url_linkedin
        self.url_company = url_company
        self.search_results = search_results
        self.novelty_score = novelty_score 
        self.activity_score = activity_score
        self.services_need_score = services_need_score
        self.total_score = total_score

    def set_search_scores(self, novelty_score, activity_score, services_need_score):
        """
        Update the scores for this search.
        
        Args:
            novelty_score (int): The novelty score of the search.
            activity_score (int): The activity score of the search.
            services_need_score (int): The services need score of the search.
        """
        self.novelty_score = novelty_score
        self.activity_score = activity_score
        self.services_need_score = services_need_score
        self.total_score = novelty_score + activity_score + services_need_score

    def get_search_period(self, previous_date= None):
        """
        Get the appropriate date range over which this search is to be conducted.
        
        Args:
            previous_date (datetime, optional): The date of the previous search, if any.
        Returns:
            str: A string representing the date range in English for LLM.
        """
        today = self.candidate.app.today

        if not previous_date:
            previous_date = today - relativedelta(months=2)
        elif not isinstance(previous_date, datetime):
            try:
                previous_date = datetime.strptime(previous_date, "%Y-%m-%d")
            except ValueError:
                previous_date = today - relativedelta(months=2)

        if previous_date > today:
            previous_date = today - relativedelta(months=3)

        months = []
        current = previous_date.replace(day=1)

        while current <= today:
            months.append(current)
            current += relativedelta(months=1)

        if len(months) == 0:
            return "Error: No valid months in range"

        if len(months) == 1:
            return months[0].strftime("%B %Y")

        if len(months) <= 6:
            month_names = [date.strftime("%B %Y") for date in months]
            if len(month_names) == 2:
                return f"{month_names[0]} and {month_names[1]}"
            else:
                return ", ".join(month_names[:-1]) + f", and {month_names[-1]}"
        else:
            start_date = months[0]
            end_date = months[-1]
            return f"{start_date.strftime('%B %Y')} - {end_date.strftime('%B %Y')}"

    def to_dict(self)                  :
        """
        Convert this search's data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary containing this search's data.
        """
        return {
            'first_name':self.candidate.first_name,
            'last_name': self.candidate.last_name,
            'company': self.candidate.company,
            'search_date': self.search_date,
            'search_event_type': self.search_event_type,
            'search_query': self.search_query,
            'search_raw': self.search_raw,
            'url_facebook': self.url_facebook,
            'url_linkedin': self.url_linkedin,
            'url_company': self.url_company,
            'search_results': self.search_results,
            'novelty_score': self.novelty_score,
            'activity_score': self.activity_score,
            'services_need_score': self.services_need_score,
            'total_score': self.total_score,
            'email_date': None, #placeholder, emails are updated later
            'email_content': None, #placeholder, emails are updated later
            'email_batch_recipient':None, #placeholder, emails are updated later
        }