"""Data management operations for the web research application."""

import pandas as pd
import numpy as np
from urllib.parse import urlparse
import random
from datetime import datetime, timedelta
import re
import logging
from core.candidate import Candidate, CandidateSearch

#======================================================================================
# DATA MANAGER
#======================================================================================

class DataManager:
    """
    Manages data operations for the web research application, including loading, cleaning,
    and processing search tasks and search history data.
    """

    def __init__(self, app):
        """
        Initialize the DataManager.

        :param app: The main application instance
        """
        self.candidates = []
        self.app = app
        self.storage_manager = app.storage_manager

    def load_df_search_tasks(self, file_path, client, required_fields=['First Name', 'Last Name', 'Company', 'Position'], sort_by=['First Name', 'Last Name', 'Company']):
        """
        Load search tasks from an Excel file and process them.

        :param file_path: Path to the Excel file containing search tasks
        :param required_fields: List of required fields in the Excel file
        :param sort_by: List of fields to sort the data by
        :return: Processed DataFrame of search tasks or None if an error occurs
        """
        try:
            # Load the file
            df_search_tasks = self.storage_manager.read_excel(file_path, client=client)

            # Confirm data contains required fields
            missing_fields = [field for field in required_fields if field not in df_search_tasks.columns]
            if missing_fields:
                msg = f"The following required fields are missing from the search tasks file: {', '.join(missing_fields)}"
                self.app.handle_error(self.app.logger, logging.CRITICAL, msg)

            # Clean the data
            df_search_tasks = self.clean_df_search_tasks(df_search_tasks)

            # Sort by name and company
            df_search_tasks = df_search_tasks.sort_values(by=sort_by)

            # Reset index
            df_search_tasks = df_search_tasks.reset_index(drop=True)

            # set the list of candidates as attributes of the DataManager
            self.candidates = [Candidate(
                                    self.app,
                                    first_name=row['First Name'],
                                    last_name=row['Last Name'],
                                    company=row['Company'],
                                    position=row['Position']
                                )
                                for _, row in df_search_tasks.iterrows()
                            ]

            return df_search_tasks

        except Exception as e:
            msg=f"load_df_search_tasks: Error loading or processing file: {str(e)}"
            self.app.handle_error(self.app.logger, logging.ERROR, msg)
            return None

    def clean_df_search_tasks(self, df):
        """
        Clean the search tasks DataFrame.

        :param df: DataFrame to clean
        :return: Cleaned DataFrame
        """
        # Remove trailing and prefixed white space
        for col in df.columns:
            df[col] = df[col].str.strip()

        # Exclude rows with no first name, last name or company. 'Position' is not required.
        df = df.dropna(subset=['First Name'])    
        df = df.dropna(subset=['Last Name'])
        df = df.dropna(subset=['Company'])

        if 'url' in df.columns:
            # Clean and validate URLs
            df['url'] = df['url'].apply(self.clean_url)

        # Remove duplicate rows
        df = df.drop_duplicates()

        # Convert name and company to title case
        # df['name'] = df['name'].str.title()
        # df['company'] = df['company'].str.title()

        return df

    def clean_url(self, url):
        """
        Clean and validate a URL.

        :param url: URL to clean and validate
        :return: Cleaned URL or None if invalid
        """
        if pd.isna(url):
            return url
        
        # Remove 'http://' or 'https://' from the beginning
        url = url.lower()
        url = url.replace('http://', '').replace('https://', '')
        
        # Validate URL
        try:
            result = urlparse(f"http://{url}")
            if all([result.scheme, result.netloc]):
                return result.netloc + result.path
            else:
                return None
        except:
            return None

    # Load previous search history

    def load_or_create_df_search_history(self, file_path, client):
        """
        Load existing search history or create a new DataFrame if it doesn't exist.

        :param file_path: Path to the search history file
        :return: DataFrame of search history
        """
        try:
            df_search_history = self.storage_manager.read_parquet(file_path, client=client)
            self.app.logger.info(f"DataFrame loaded from {file_path}")
            return df_search_history

        except Exception as e:
            self.app.logger.info("error reading client's history file, creating blank")
            # If there's an error loading, we'll create a new DataFrame
        
        # of not exists, then create dataframe as blank
        columns = {
                #"record_id": pd.StringDtype(),
                "first_name": pd.StringDtype(),
                "last_name": pd.StringDtype(),
                "company":pd.StringDtype(), 
                "search_date": 'datetime64[ns]',
                "search_event_type": pd.StringDtype(),
                "search_query": pd.StringDtype(),
                "search_raw": pd.StringDtype(),
                "url_facebook": pd.StringDtype(),
                "url_linkedin": pd.StringDtype(),
                "url_company": pd.StringDtype(),
                "search_results": pd.StringDtype(),
                "novelty_score": pd.Int64Dtype(),
                "activity_score": pd.Int64Dtype(),
                "services_need_score": pd.Int64Dtype(),
                "total_score": pd.Int64Dtype(),
                "email_date":'datetime64[ns]',
                "email_content": pd.StringDtype(),
                "email_batch_recipient":pd.StringDtype()
            }

        df_search_history = pd.DataFrame(columns=columns.keys()).astype(columns)
        self.app.logger.info(f"Empty DataFrame created with specified structure")
        return df_search_history


    def prepare_searches(self, df_search_tasks, df_search_history, shuffle= True):
        """
        Prepare and merge search tasks and search history data for processing.

        :param df_search_tasks: DataFrame containing search tasks
        :param df_search_history: DataFrame containing search history
        :param shuffle: Whether to shuffle the resulting DataFrame
        :return: Merged and prepared DataFrame
        """
        # Clean string fields in df_search_tasks
        for column in df_search_tasks.columns:
            df_search_tasks[column] = df_search_tasks[column].apply(lambda x: re.sub(r'[^\x00-\x7F]+', '', str(x)))

        # Merge dataframes
        merged_df = pd.merge(
            df_search_tasks,
            df_search_history,
            left_on=['First Name', 'Last Name', 'Company'],
            right_on=['first_name', 'last_name', 'company'],
            how='left'
        )
        
        # Drop redundant columns and rename fields
        merged_df = merged_df[['First Name', 'Last Name', 'Company', 'Position', 'search_date', 'search_event_type', 
                                'search_query', 'search_raw', 'url_facebook', 'url_linkedin', 'url_company', 'search_results', 'total_score']]
        merged_df = merged_df.rename(columns={
            'First Name': 'first_name',
            'Last Name': 'last_name',
            'Company': 'company',
            'Position': 'position',
            'search_date': 'search_date_previous'
        })
        
        # Set eligibility for processing
        current_date = datetime.now()
        merged_df['eligible_for_processing'] = (
            (merged_df['search_date_previous'].isna()) | 
            (merged_df['search_date_previous'] < current_date - timedelta(days=30))
        )
        
        # Replace NA and NaT with None
        merged_df = merged_df.replace({pd.NA: None, pd.NaT: None})
        merged_df = merged_df.where(pd.notnull(merged_df), None)

        # Shuffle if requested
        if shuffle:
            merged_df = merged_df.sample(frac=1).reset_index(drop=True)

        # Filter out freelancers, using ~ for 'not'
        merged_df = merged_df[~merged_df['position'].str.lower().str.startswith('freelance')]

        return merged_df

    def create_candidates_from_dataframe(self, df):
        """
        Create Candidate objects from a prepared DataFrame.

        :param df: DataFrame containing candidate information
        :return: List of Candidate objects
        """
        candidates = []
        for _, row in df.iterrows():
            candidate = Candidate(self.app, row['first_name'], row['last_name'], row['company'], row['position'])
            if pd.notnull(row['search_date_previous']):
                candidate.add_search(
                    row['search_date_previous'],
                    row['search_event_type'],
                    row['search_query'],
                    row['search_raw'],
                    row['url_facebook'],
                    row['url_linkedin'],
                    row['url_company'],
                    row['search_results'],
                    #row['novelty_score'],
                    #row['activity_score'],
                   # row['services_need_score'],
                    row['total_score'],
                    #row['email_date'],
                    #row['email_content']
                )
            candidates.append(candidate)
        return candidates

    def get_batch(self, candidates,  batch_size):
            """
            Select a batch of candidates for processing.

            :param candidates: List of all candidates
            :param batch_size: The number of candidates to select
            :return: A list of selected Candidate objects
            """
            # Filter eligible candidates
            eligible_candidates = [c for c in candidates if c.is_eligible_for_processing()]

            # Separate candidates without previous searches and those with searches
            new_candidates = [c for c in eligible_candidates if not c.searches]
            existing_candidates = [c for c in eligible_candidates if c.searches]

            # First, select all new candidates (up to batch_size)
            selected_candidates = new_candidates[:batch_size]

            # If we still need more candidates, sample from existing candidates
            remaining_slots = batch_size - len(selected_candidates)

            if remaining_slots > 0 and existing_candidates:
                # Calculate selection probabilities for existing candidates
                scores = [c.get_latest_search().total_score for c in existing_candidates]
                max_score = max(scores) if scores else 1  # Avoid division by zero
                probabilities = [score / max_score for score in scores]

                # Sample based on probabilities
                additional_candidates = np.random.choice(
                    existing_candidates,
                    size=min(remaining_slots, len(existing_candidates)),
                    replace=False,
                    p=probabilities
                ).tolist()

                selected_candidates.extend(additional_candidates)

            return selected_candidates