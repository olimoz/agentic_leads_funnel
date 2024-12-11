# B2B Automated Leads Funnel

A Python application that automates a B2B leads funnel.
AI agents conduct web research on people listed in a spreadsheet.
The agents shortlist those contacts who recently published 'buy signals', given what they know about your business

This application executes as a daily batch operation, then on a weekly schedule it emails the user a .docx report of...
- how many searches were conducted
- the shortlist of contacts
- why they were chosen
- a draft introductory email

## Project Structure

```
leads_funnel/
├── agents/         	# Search and analysis agents
├── core/           	# Core business logic
├── config/ 	        # Configuration and logging
├── clients/         	# Client Data,
|	├── ThinkVideo/   	# Client 1. One folder per client
|	└── ChoiceMaster/   # Client 2. One folder per client
├── ui/             	# User interface components
├── azure_function/ 	# Azure function for triggering the app in the cloud
└── for_docker/     	# Docker configuration
```

Each client requires their own folder, the app will seek all such folders in the current directory, confirm a valid subscription exists and then process the contacts therein

## Process

The process followed by the app is as follows:
- For details, see: (docs/sequence_diagram.svg)[docs/sequence_diagram.svg]

### Initial Setup:
- Application initialization
- Storage manager setup
- Loading of pricing data
	- see api_pricing.xlsx
- Creation of client managers
	- one per client, each client has their own folder of data
	- check client subscription status in subscriptions.xlsx

### Client Processing Loop:
- Loading search tasks and history
- Processing candidates in batches
- Performing searches and calculating scores

### Search Process:
- Query generation
- Search execution
- Score calculation
- etc (see all steps in process_client() method)

### Email Processing:
- Content generation
- Batch email sending via AWS SES (Simple Email Service)

### Data Storage:
- Saving results to client's copy of df_search_history.parquet

### Final Steps:
- Consumption of API tokens and searches is saved to each client's copy of df_consumption.parquet
- Application completion

## Data

app_data folder
- `subscriptions.xlsx`: Master list of client subscriptions
- `api_pricing.xlsx`: Master list of API pricing data
- `config_app.yaml`: App configuration

ui folder
- `config_login.yaml`: UI authentication configuration

For each client we have a folder of contacts to be searched, ai agent prompts, email templates and results
`clients/client_name`
- `config_client.yaml`: Client configuration
- `df_search_tasks.xlsx`: Client contact list and search tasks
- `prompt_searchproposalagent.txt`: Default search proposal template
- `prompt_urlextractionagent.txt`: Default URL extraction template
- `prompt_targetscoreagent.txt`: Default target scoring template
- `prompt_resultscomparisonagent.txt`: Default results comparison template
- `prompt_searchresultsrankingagent.txt`: Default search results ranking template
- `template_email.md`: Default email template
- `prompt_businessdescription.md`: Default business description template
- `prompt_emailproposalagent.txt`: Default email proposal template
- `df_search_history.xlsx`: Client search results. 'First Name', 'Last Name' and 'Company' are required.

## Config

Install dependencies:
```bash
pip install -r requirements.txt
```

### App configuration

Each client has a a configuration file in their respective folder:
- client_name/config_client.yaml

Set up environment variables in the app's .env file in app root directory
In Production this is done via ENV params in the docker file, see below section on deployment.
In Development this is done via the app's .env file:
- ENVIRONMENT=DEV

### Client configuration

The app has a configuration file:
- config_app.yaml

Set up environment variables in each client's .env file, as found in their folder
- OPENAI_API_KEY
- TAVILY_API_KEY
- PPLX_API_KEY
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY

### UI configuration

A UI has been built as a PoC using Streamlit. It is designed purely for development, not production.
In a development environment the UI is run locally, in a browser, and the app is run locally.

UI Athentication is managed by streamlit-authenticator, so is basic, see:
- UI/config_login.yaml
- UI/generate_passwords.py

## Intended Deployment

1. Package app into docker container, as per DockerInstructions.txt
2. Upload container to Azure Container Registry, as per DockerInstructions.txt
3. Ensure AzureFunction has been deployed in Azure (see AzureFunction folder)
4. This function triggers the container on a schedule, it runs in a Azure Container Service
5. Having executed all lead searches in the daily batch the container should shut down
	- Note, the API calls occassionally hang and the container does not shut down
6. During execution the app updates files in an Azure Blob Storage Container
	- df_search_history.parquet, the searches completed the results found
	- df_consumption.parquet, the api tokens and searches incurred. Convert to charges via api_pricing.xlsx

## Production vs Development

- An environment variable must be used to specify whether execution is in production (PROD) or development (DEV).
In production the app will seek all data files in Azure Blob storage. 

- In development the app will seek all data files in a local folder with each client's name.
Notably, the client's config_client.yaml specifies the batch size, how many searches to conduct. Use a small number, say 6, for testing so as to minimise API charges in test.

### If ENV=PROD 
Requires Docker launched from Azure. All docker images need a 'Dockerfile'. The 'Dockerfile' contents are as below.
NB. Azure storage connection string is required for connection to Azure Blob Storage Container

```bash
FROM python:3.10.14
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=webresearchapp;AccountKey=...;EndpointSuffix=core.windows.net"
ENV AZURE_CONTAINER_NAME=webresearchapp
ENV ENVIRONMENT=PROD
COPY . .
RUN chmod +x app.py
CMD ["python", "app.py"]
```

Build docker image locally, with name eg 'webresearchapp':
```bash
docker build -t webresearchapp .
```

Test docker image locally, assuming image called 'webresearchapp':
```bash
docker run -it webresearchapp
```

Then push to Azure Container Registry and execute from there
Code example below, assuming docker image called 'webresearchapp'
```bash
az login
az acr login --name webresearchapp
docker tag webresearchapp:latest webresearchapp.azurecr.io/webresearchapp:latest
docker push webresearchapp.azurecr.io/webresearchapp:latest
```

### If ENV=DEV

Ensure only small number of searches conducted, else test consumes lots of credits!
This is done via each client's config_client.yaml, e.g.:
BATCH_SIZE: 6

Then simply execute:
```bash
python app.py
```

## Logging

The app saves activity logs to the app root folder.
View logs for clues to errors.