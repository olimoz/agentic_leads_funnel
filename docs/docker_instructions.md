# INSTRUCTIONS FOR USE OF DOCKER

This app is intended for use as a batch process.

In production this suits docker distributions well, as the image can be executed in a container and then shut down automatically.
This minimises usage of cloud resources.

This is not a concern in development, so no Docker work required when developing and testing.

Below are instructions on use of Docker to package the app as a docker image and publish to an Azure container registry.
From that registry the container can be executed on a scheduled basis.
This is triggered by an Azure function.

## BUILD DOCKER IMAGE

Open a terminal, go to project folder, e.g.:

```bash
cd /home/oliver/MindSearch/mindsearch/agent/agent_candidate_search/for_docker
```

Ensure requirements.txt specifies versions of Langchain, else you get the 'no OpenAI' error
Ensure the folder with the app has a docker file, contents like this:

```bash
FROM python:3.10.14
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV AZURE_STORAGE_CONNECTION_STRING="..."
ENV AZURE_CONTAINER_NAME=webresearchapp
ENV ENVIRONMENT=PROD
COPY . .
RUN chmod +x app.py
CMD ["python", "app.py"]
```

Ensure dockerfile includes any environment variables as per above example
NOTE, .env does NOT WORK when passing like this:

```bash
echo DO NOT APPLY .env LIKE THIS
docker build -t --env-file .env webresearchapp .
```

Build the folder into a Docker image (list of files, like a drive)

```bash
docker build -t webresearchapp .
```
## POSSIBLE ISSUE WITH TYPE HINTS

Python in Docker may be very picky. Removing type hints can help if you meet this problem 

```bash
strip-hints app.py > app_no_hints.py
```

## TO EXECUTE LOCALLY

Execute the image into a Docker container (executable environment)

```bash
docker run -it webresearchapp
echo OR, if access to internet is a problem...
docker run -it webresearchapp --dns 8.8.8.8 --dns 8.8.4.4
```

## TO INSPECT CONTAINER
NB, a running docker image is correctly called a container

- list docker containers, running or stopped
```bash
docker ps -a
```

- you can pass env variables and execute specific py files:
```bash
docker run -it -w /app -e ENV_VAR=value your-image-name python main.py
```

-To access a docker shell before the app initiates
```bash
docker run -it --entrypoint /bin/bash webresearchapp
```

## DEPLOYMENT TO AZURE CONTAINER REGISTRY

Login to Azure container registry, which you create via the portal.

```bash
az login
az acr login --name webresearchapp
```

Tag the local docker image with the Azure container registry url
where Azure registry is at webresearchapp.azurecr.io
and the local docker image is called webresearchapp

```bash
docker tag webresearchapp:latest webresearchapp.azurecr.io/webresearchapp:latest
```

Then push image to container registry

```bash
docker push webresearchapp.azurecr.io/webresearchapp:latest
```

## CREATE AZURE CONTAINER INSTANCE (ACI)

The container will need to run in a container instance.
So, wia the Azure portal (portal.azure.com), create a new container instance which points to the container registry

## CREATE AZURE FUNCTION TO SCHEDULE THE ACI

The app runs its tasks in a batch process, so the container will stop when the app exits, 
But, we need to restart it on a schedule, say, daily at 5am.
So we use an Azure Function, see the azure_function folder of the repo.

In VS Code you must create a local workspace with the function and deploy to Azure, after it passes the debug test.

```python

import azure.functions as func
import datetime
import logging
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient

app = func.FunctionApp()

@app.timer_trigger(schedule="0 0 5 * * *", arg_name="myTimer", run_on_startup=True, use_monitor=False) 
def timer_trigger(myTimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if myTimer.past_due:
        logging.info('The timer is past due!')

    credential = DefaultAzureCredential()
    client = ContainerInstanceManagementClient(
        credential=credential,
        subscription_id='8fba350f-2e21-4051-a76c-0e8b5feaa277'  # Replace with your subscription ID
    )

    client.container_groups.begin_start(
        resource_group_name='WebResearchApp',
        container_group_name='webresearchapp'
    )

    logging.info(f"Container 'webresearchapp' started at {utc_timestamp}")
```

## GRANT AZURE FUNCTION RIGHTS TO CONTAINER

The azure function needs access permissions in order to trigger the container

1. Enable Managed Identity on the Azure Function:
- Go to the Azure Portal.
- Navigate to your Azure Function App.
- Under "Settings," select Identity.
- Enable the System Assigned Managed Identity.

2. Assign Role to Managed Identity:
- After enabling the Managed Identity for the Function, you'll need to assign it the necessary permissions.
- Navigate to the Azure Container Instance you're trying to trigger.
- Select Access Control (IAM) on the left.
- Click on Add Role Assignment.
- Choose the role "Contributor" or "Container Instance Contributor" (the latter is more specific).
- In the Assign access to field, select "Managed identity".
- In the Select field, choose the managed identity that was enabled for the Azure Function.

