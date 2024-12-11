"""
Client Manager module for handling client-specific operations and configuration.
"""
import io
import os
import logging
import yaml
import traceback
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import pandas as pd
import numpy as np
import asyncio
from dotenv import load_dotenv # For loading environment variables
from langchain_openai import ChatOpenAI
from aiolimiter import AsyncLimiter

from core.data_manager import DataManager
from core.candidate_pipeline import CandidatePipeline
from core.email_manager import EmailManager
from core.consumption_tracker import ConsumptionTracker
from agents.email_proposal import EmailProposalAgent

#======================================================================================
# CLIENT MANAGER
#======================================================================================

class ClientManager:
    """
    Manages client-specific operations including configuration, data processing, and email handling.
    There will be one or more clients whose documents we process per execution
    """
    def __init__(self, app, client, client_monthly_budget, today):
        """
        Initialize the ClientManager.

        Args:
            app (WebResearchApp): The main application instance.
            client (str): client name
        """
        self.app = app
        self.client = client
        self.client_monthly_budget = client_monthly_budget
        self.today = today
        self.storage_manager = app.storage_manager

        # print("init client manager")
        self.config, self.any_errors = self.read_config_client()

        # print(""any errors: {self.any_errors}")
        if not self.any_errors:
            self.data_manager = DataManager(self.app)
            self.email_proposal_agent = EmailProposalAgent(self.app)
            # print("email complete")
            self.llm = self.initialize_llm(model_name = self.config['LLM_SEARCH'])
            # print("init llm complete")
            self.llm_email = self.initialize_llm(model_name = self.config['LLM_EMAIL'])
            # print("init llm_email complete")
            self.email_manager = EmailManager(self.config, self.llm_email, self.client, self.app) 
            self.candidate_pipeline = CandidatePipeline(self.app, self.config, self.llm, self.llm_email)

    def read_config_client(self):
        """
        Read and validate the client's configuration files.

        Returns:
            Tuple[Dict[str, Any], bool]: A tuple containing the configuration dictionary and a boolean indicating if any errors occurred.
        """
        config_file_path = 'config_client.yaml'
        env_file_path = '.env'
        any_errors = False
        config = {}
        # print("reading yaml")
        # Load client's .env file
        if not self.storage_manager.file_exists(env_file_path, client=self.client):
            self.app.handle_error(self.app.logger, logging.CRITICAL, f"Client's .env file not found: {env_file_path}")
            any_errors = True
        else:
            env_content = self.storage_manager.read_file(env_file_path, client=self.client)
            load_dotenv(stream=io.StringIO(env_content))

        # Load client's yaml file
        if not self.storage_manager.file_exists(config_file_path, client=self.client):
            self.app.handle_error(self.app.logger, logging.CRITICAL, f"Client's YAML configuration file not found: {config_file_path}")
            any_errors = True
        else:
            config_content = self.storage_manager.read_file(config_file_path, client=self.client)
            try:
                config = yaml.safe_load(config_content)
                print(config)
            except yaml.YAMLError as e:
                self.app.handle_error(self.app.logger, logging.CRITICAL, f"Error parsing client YAML configuration file for {config_file_path}: {str(e)}")
                any_errors = True

        # Validate required configuration items
        required_keys = ['CLIENT',  'BATCH_SIZE', 'MINI_BATCH_SIZE',
                         'LLM_SEARCH', 'LLM_EMAIL', 'MAX_TAVILY_SEARCHES', 'MAX_PPLX_SEARCHES',
                         'EMAIL_BATCH_RECIPIENT', 'EMAIL_DAYS_OF_WEEK','EMAIL_USER','MAX_EMAILS']

        for key in required_keys:
            if key not in config:
                self.app.handle_error(logging.CRITICAL, f"Missing required configuration key: {key}")
                any_errors = True
                return config, any_errors

        # Validate the values
        if not config.get('SEND_PROPOSED_EMAILS', None) in [True, False]: 
            self.app.handle_error(self.app.logger, logging.CRITICAL, "Must specify SEND_PROPOSED_EMAILS as either True or False")
            any_errors = True

        if not 0 < config.get('MAX_TAVILY_SEARCHES', 0) < 20:
            self.app.handle_error(self.app.logger, logging.ERROR,"MAX_TAVILY_SEARCHES must be between 1 and 20. Prefer 5.")
            any_errors = True

        if not 0 < config.get('MAX_PPLX_SEARCHES', 0) < 10:
            self.app.handle_error(self.app.logger, logging.ERROR,"MAX_PPLX_SEARCHES must be between 1 and 10. Prefer 2.")
            any_errors = True

        if not 0 < config.get('BATCH_SIZE', 0) < 1000:
            self.app.handle_error(self.app.logger, logging.ERROR,"BATCH SIZE must be between 1 and 1000.")
            any_errors = True

        if config.get('MINI_BATCH_SIZE', 0) > config.get('BATCH_SIZE', 0):
            self.app.handle_error(self.app.logger, logging.ERROR,"MINI BATCH SIZE must be <= BATCH_SIZE. Prefer 3 due to 20 calls/min limit with Perplexity.")
            any_errors = True

        if config.get('LLM_SEARCH') not in ["gpt-4o-mini", "gpt-4o", "gpt-4"]:
            self.app.handle_error(self.app.logger, logging.ERROR,"LLM_SEARCH must be an Open AI model: gpt-4o-mini, gpt-4o, or gpt-4.")
            any_errors = True

        if not config.get('LLM_EMAIL').startswith("gpt-4o"):
            self.app.handle_error(self.app.logger, logging.ERROR,"LLM_EMAIL must be an Open AI model: gpt-4o-mini, gpt-4o, gpt-4o-2024-05-13 etc..")
            any_errors = True

        if not config.get('EMAIL_DAYS_OF_WEEK'):
            self.app.handle_error(self.app.logger, logging.ERROR,"There must be at least one day of the week when the client should be emailed with progress.")
            any_errors = True

        # set Brave limit based on Tavily
        config['MAX_BRAVE_SEARCHES'] = config.get('MAX_TAVILY_SEARCHES', 0)

        # Load API keys and other sensitive data from environment variables
        env_vars = ['PPLX_API_KEY', 'TAVILY_API_KEY', 'OPENAI_API_KEY', 'BRAVE_API_KEY',
                    'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']

        for var in env_vars:
            value = os.environ.get(var)
            if value is None:
                self.app.handle_error(self.app.logger, logging.ERROR, f"Missing client environment variable {var} in {env_file_path}")
                any_errors = True
            config[var] = value

        self.app.logger.info(f"Loaded config for client: {self.client}")
        # print(""Existing config: {config}")
        return config, any_errors

    
    async def process_client(self):
        """
        Process the client's data, including loading search tasks, performing searches, and handling emails,
        while respecting the client's monthly budget.
        """

        # checking for config errors before proceeding
        if self.any_errors:
            self.app.handle_error(self.app.logger, logging.ERROR, f"Skipping client processing due config errors in folder: {self.client}")
            return

        # checking for budget before proceeding
        df_consumption_filepath = self.app.config['DF_CONSUMPTION_FILENAME']
        current_month_start = self.today.replace(day=1)
        # print(f'current month start: {current_month_start}')
        costs_month_to_date = self.app.calculate_api_costs( df_consumption_filepath, 
                                                            self.client, 
                                                            date_from=current_month_start, 
                                                            date_to=None)

        costs_month_to_date = min(costs_month_to_date['cost'].sum(),0)

        if costs_month_to_date >= self.client_monthly_budget:
            self.app.logger.warning(f"Monthly budget already exceeded for client {self.client}. Stopping processing.")
            return

        # continue to process client
        self.app.logger.info(f"Configuring pipeline for: {self.client} ")

        df_search_tasks = self.data_manager.load_df_search_tasks(self.app.config['DF_SEARCH_TASKS_FILENAME'], client=self.client)
        self.app.logger.info(f"Loaded df_search_tasks for: {self.client} ")

        df_search_history = self.data_manager.load_or_create_df_search_history(self.app.config['DF_SEARCH_HISTORY_FILENAME'], client=self.client)
        self.app.logger.info(f"Loaded df_search_history for: {self.client}. Length: {str(len(df_search_history))} records")

        merged_df = self.data_manager.prepare_searches(df_search_tasks, df_search_history)
        candidates = self.data_manager.create_candidates_from_dataframe(merged_df)
        self.app.logger.info(f"There are {str(len(candidates))} valid candidates for search.")

        batch = self.data_manager.get_batch(candidates, self.config['BATCH_SIZE'])
        self.app.logger.info(f"As instructed, this batch will process {str(len(batch))}.")

        semaphore = asyncio.Semaphore(10)
        search_limiter_perplexity = AsyncLimiter(20, 60)
        search_limiter_tavily = AsyncLimiter(20, 60)

        searches_all = []
        processed_candidates = set()  # Track which candidates we've already processed

        async with ConsumptionTracker(self.app, self.client) as tracker:

            # Process each mini batch sequentially
            for i in range(0, len(batch), self.config['MINI_BATCH_SIZE']):
                current_mini_batch = batch[i:i+self.config['MINI_BATCH_SIZE']]
                
                # Filter out any candidates we've already processed
                current_mini_batch = [
                    candidate for candidate in current_mini_batch 
                    if candidate not in processed_candidates
                ]
                
                if not current_mini_batch:  # Skip if all candidates in this batch were already processed
                    continue

                # log activity
                msg = f"Processing mini batch starting at index {i}. Batch Size: {self.config['BATCH_SIZE']}. Mini Batch Size: {self.config['MINI_BATCH_SIZE']}"
                print(msg)
                self.app.logger.info(msg)

                # prep async tasks
                try:
                    tasks = []
                    for candidate in current_mini_batch:
                       
                        tasks.append(
                            self.candidate_pipeline.process(
                                candidate, 
                                self.client, 
                                semaphore, 
                                search_limiter_perplexity, 
                                search_limiter_tavily
                            )
                        )
                    
                    try:
                        # Process this mini batch
                        results = await asyncio.gather(*tasks)
                        
                        # Log consumption and results
                        for candidate, (search, consumptions) in zip(current_mini_batch, results):
                            searches_all.append(search)
                            tracker.add_consumption(consumptions)
                            processed_candidates.add(candidate)  # Mark this candidate as processed
                            
                        # Log completion of this batch
                        msg = f"Completed processing mini batch starting at index {i}"
                        print(msg)
                        self.app.logger.info(msg)

                    except Exception as e:
                        error_msg = f"Error processing mini batch starting at index {i}:\n"
                        error_msg += f"Error type: {type(e).__name__}\n"
                        error_msg += f"Error message: {str(e)}\n"
                        error_msg += "Traceback:\n"
                        error_msg += traceback.format_exc()
                        self.app.logger.error(error_msg)
                        print(error_msg)
                        continue

                except Exception as e:
                    error_msg = f"Error preparing tasks for mini batch at index {i}:\n"
                    error_msg += f"Error type: {type(e).__name__}\n"
                    error_msg += f"Error message: {str(e)}\n"
                    error_msg += "Traceback:\n"
                    error_msg += traceback.format_exc()
                    self.app.logger.error(error_msg)
                    print(error_msg)
                    continue

        # Save search history
        df_searches_filepath = self.app.config['DF_SEARCH_HISTORY_FILENAME']
        if searches_all:
            df_searches = pd.DataFrame([search.to_dict() for search in searches_all])
            self.storage_manager.append_to_parquet(df_searches, df_searches_filepath, client=self.client)
            msg = f"Completed batch of searches"
            print(msg)
            self.app.logger.info(msg)

        # log completion
        msg = f"Saved batch search results to : {df_searches_filepath}"
        print(msg)
        self.app.logger.info(msg)

        # process emails
        await self.process_emails()

        # log completion
        self.app.logger.info(f"Processing complete for : {self.client}")

    async def process_emails(self):
        """
        Process and send emails for the client based on search results and configuration.
        """
        msg = f"Start email processing..."
        print(msg)
        self.app.logger.info(msg)

        today = self.app.today
        if today.strftime("%A").lower() in [day.lower() for day in self.config['EMAIL_DAYS_OF_WEEK']]:
            df_search_history = self.data_manager.load_or_create_df_search_history(self.app.config['DF_SEARCH_HISTORY_FILENAME'], client=self.client)
            df_email_candidates, consumption_get_email_candidates = await self.email_manager.get_email_candidates(df_search_history)

            # convert consumption to dataframe
            df_consumption_a = pd.DataFrame(consumption_get_email_candidates)
            df_consumption_a['client'] = self.client
            df_consumption_a['search_date'] = np.datetime64(self.app.today, 'us')
            columns = ['client', 'search_date'] + [col for col in df_consumption_a.columns if col not in ['client', 'search_date']]
            df_consumption_a = df_consumption_a[columns]

            # how many searches have been conducted since the last time we sent emails?
            last_email_date = pd.Timestamp.min
            if df_search_history is not None and not df_search_history.empty:
                last_email_date = df_search_history['email_date'].max()
                if pd.isnull(last_email_date):
                    last_email_date = pd.Timestamp.min  # Encompass all search history if no valid date

            searches_since_last_email = len(df_search_history[df_search_history['search_date'] > last_email_date])

            # log the sending of emails
            msg = f"Email actions planned:\n{df_email_candidates[['first_name', 'last_name', 'company', 'search_date']].to_string()}"
            print(msg)
            self.app.logger.info(msg)

            if not df_email_candidates.empty:

                email_updates = []
                email_consumption_total = {}

                for index, candidate in df_email_candidates.iterrows():
                    self.app.logger.info(f"Processing email for {candidate.first_name} {candidate.last_name}")
                    email_status, email_update, consumption = await self.process_email_candidate(candidate, index)
                    email_updates.append(email_update)

                    # log progress
                    msg = f"Completed processing email for {candidate.first_name} {candidate.last_name}"
                    self.app.logger.info(msg)
                    print(msg)

                    for key, value in consumption.items():
                        if key in ['function', 'model']:
                            email_consumption_total[key] = value  # Simply store the last value for string fields
                        else:
                            email_consumption_total[key] = email_consumption_total.get(key, 0) + value  # Sum for numeric fields

                # Update df_search_history with the email date, email content and recipient.
                for update in email_updates:
                    df_search_history.loc[update['index'], update['columns']] = update['values']

                # save the updated file (Will get big over time!)
                self.storage_manager.to_parquet(df_search_history, self.app.config['DF_SEARCH_HISTORY_FILENAME'], client=self.client)

                if not self.config['SEND_PROPOSED_EMAILS']:
                    
                    await self.send_batch_email(df_search_history, email_updates, searches_since_last_email)
                          
                # log the sending of emails
                msg = f"Number of email actions completed: {str(len(email_updates))}"
                print(msg)
                self.app.logger.info(msg)

                # convert consumption to dataframe
                df_consumption_b = pd.DataFrame([{**{'client': self.client, 'search_date': today}, **email_consumption_total}])

                # ensure consumption_a and consumption_b have same date format, pandas datetime microseconds (datetime[us]), not nanoseconds
                df_consumption_b['search_date'] = df_consumption_b['search_date'].astype('datetime64[us]')

                # pandas concat the two consumptions
                df_consumption = pd.concat([df_consumption_a, df_consumption_b], axis=0, ignore_index=True)

                self.storage_manager.append_to_parquet(df_consumption, self.app.config['DF_CONSUMPTION_FILENAME'], client=self.client)

        else:
            msg = f"No emails sent. Today is {today.strftime('%A')}, which is not a designated day: {str(self.config['EMAIL_DAYS_OF_WEEK'])} for {self.client}"
            print(msg)
            self.app.logger.info(msg)


    async def process_email_candidate(self, candidate, index):
        """
        Process an individual email candidate.

        Args:
            candidate (pd.Series): The candidate's information.
            index: The index of the candidate in the DataFrame.

        Returns:
            Tuple[bool, Dict[str, Any], Dict[str, Any]]: A tuple containing the email status, update information, and consumption data.
        """
        email_content, consumption = await self.email_proposal_agent.run(
            self.llm_email,
            candidate['first_name'],
            candidate['last_name'],
            candidate['company'],
            candidate['search_results'],
            self.client
        )

        email_sent_date = self.app.today

        if self.config['SEND_PROPOSED_EMAILS']:
            email_subject = f"Proposed email for {candidate['first_name']} {candidate['last_name']} of {candidate['company']}"
            email_content += f"\n=======================\nThis proposed email follows from the below search results:\n{candidate['search_results']}"
            email_status = await self.email_manager.send_email(email_content, email_subject)

             # log the outcome
            msg = f"{email_status}: {email_subject}"
            print(msg)
            self.app.logger.info(msg)

        else:
            # not sent yet (may be sent in later batch email function, send_batch_email() )
            email_status = False

        update = {
            'index': index,
            'columns': ['email_date', 'email_content', 'email_batch_recipient'],
            'values': [email_sent_date, email_content, self.config['EMAIL_BATCH_RECIPIENT']]
        }

        return email_status, update, consumption

    async def send_batch_email(self, df_search_history, email_updates, searches_since_last_email):
        """
        Send a batch email with updated search history information.

        Args:
            df_search_history (pd.DataFrame): The search history DataFrame.
            email_updates (List[Dict[str, Any]]): A list of email updates.
        """
        updated_indices = [update['index'] for update in email_updates]
        df_updated_rows = df_search_history.loc[updated_indices]

        key_fields = ["first_name", "last_name", "company", "search_date", "search_results", "activity_score", "services_need_score", "email_content"]
        df_updated_rows = df_updated_rows[key_fields]

        today = self.app.today.strftime("%Y%m%d_%H%M")

        # if attachment_path is excel file
        # attachment_path = self.app.config['DF_SEARCH_HISTORY_UPDATES_FILENAME']
        # self.storage_manager.to_excel(df_updated_rows, attachment_path, client=self.client)

        # if attachment_path is docx file
        attachment_path = f"leads_report_{today}.docx"
        self.email_manager.create_word_report(df_updated_rows, attachment_path, searches_since_last_email)

        email_content = self.storage_manager.read_file(self.app.config['EMAIL_TEMPLATE_SPREADSHEET_FILENAME'], client=self.client)
        email_date_as_string = datetime.now().strftime("%d-%b")
        email_subject = f"Proposed Marketing Emails as of {email_date_as_string}"

        msg = await self.email_manager.send_email(email_content, email_subject, attachment_path, self.client)

        # log the outcome
        self.app.logger.info(msg)

    def initialize_llm(self, model_name):
        """
        Initialize the language model for the client.
        OpenAI is preferred because of tool calling capabilities in the small (cheap) model, GPT-4o-mini.

        Returns:
            ChatOpenAI: An instance of the ChatOpenAI model.
        """
        # print(""Initializing ChatOpenAI LLM...{model_name}. Key: {os.getenv('OPENAI_API_KEY')}")

        try:
            llm = ChatOpenAI(model_name=model_name, temperature=0.5)
        except Exception as e:
            print(e)
        # print(""DONE: Initializing ChatOpenAI LLM...{model_name}")
        return llm

    async def run(self):
        """
        Run the main client processing pipeline.
        """
        try:
            if self.any_errors:
                self.app.handle_error(self.app.logger, logging.ERROR, f"Skipping client run due to configuration errors: {self.client}")
                return

            await self.process_client()

        except Exception as e:
            msg = f"An error occurred while running the client manager: {str(e)}"
            self.app.handle_error(self.app.logger, logging.CRITICAL, msg)
