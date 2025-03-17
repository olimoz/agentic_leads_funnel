import azure.functions as func
import datetime
import logging
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient

app = func.FunctionApp()

@app.timer_trigger(schedule="0 0 5 * * *", arg_name="myTimer", run_on_startup=False) 
def start_container(myTimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if myTimer.past_due:
        logging.info('The timer is past due!')

    credential = DefaultAzureCredential()
    client = ContainerInstanceManagementClient(
        credential=credential,
        subscription_id=''  # Replace with your subscription ID
    )

    client.container_groups.begin_start(
        resource_group_name='WebResearchApp',
        container_group_name='webresearchapp'
    )

    logging.info(f"Container 'webresearchapp' started at {utc_timestamp}")

@app.timer_trigger(schedule="0 30 6 * * *", arg_name="cleanupTimer")
def cleanup_container(cleanupTimer: func.TimerRequest) -> None:
    credential = DefaultAzureCredential()
    client = ContainerInstanceManagementClient(
        credential=credential,
        subscription_id=''
    )

    try:
        client.container_groups.stop(
            resource_group_name='WebResearchApp',
            container_group_name='webresearchapp'
        )
        
        logging.info("Container stopped successfully")
    except Exception as e:
        logging.error(f"Error stopping container, or container already stopped: {str(e)}")