from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

import concurrent.futures
import datetime
import json
import math
import requests

"""
If this action succeeds, it will return a json in the following format, to match the json-adapter format:
{
    "results": [
        # logs
    ]
}
"""

BASE_URL = "https://api.logz.io/"
SEARCH_LOGS_API_SUFFIX = "v2/security/rules/events/logs/search"
DEFAULT_PAGE_SIZE = 25
MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 1000
GENERAL_INSIGHT_TYPE = 0

@output_handler
def main():
    siemplify = SiemplifyAction()
    status = EXECUTION_STATE_FAILED # default. will be changed only if logs retrieved and parsed to json successfully.
    num_logs = 0
    logzio_token = siemplify.extract_configuration_param('Logzio',"logzio_security_token", default_value="-", is_mandatory=True)
    if logzio_token == "-" or logzio_token == "":
        siemplify.LOGGER.error("Error occurred: no Logzio API token! Exiting.")
        raise ValueError
    logzio_region = siemplify.extract_configuration_param('Logzio',"logzio_region", default_value="")
    url = get_logzio_api_endpoint(siemplify, logzio_region)
    logs_response = execute_logzio_api(siemplify, logzio_token, url)
    if logs_response is not None:
        logs_json, num_logs = create_json_result(siemplify, logs_response, logzio_token, url)
        if logs_json is not None:
            siemplify.result.add_result_json(logs_json)
            status = EXECUTION_STATE_COMPLETED
            add_insights(siemplify, logs_json)
            
    
    output_message = get_output_msg(status, num_logs)
    is_success = status == EXECUTION_STATE_COMPLETED
    siemplify.end(output_message, is_success, status)
    
    
    
def execute_logzio_api(siemplify, api_token, url, page_number=1):
    """ Sends request to Logz.io and returnes the response, if applicable """
    alert_event_id = siemplify.extract_action_param("alert_event_id", default_value="", is_mandatory=True, print_value=True)
    if alert_event_id == "":
        siemplify.LOGGER.error("Error occurred: no alert_event_id! Exiting.")
        raise ValueError
    try:
        siemplify.LOGGER.info("Fetching page number {}".format(page_number))
        new_request = create_request_body_obj(siemplify, alert_event_id, page_number)
        new_logs = fetch_logs_by_event_id(api_token, new_request, url, siemplify, alert_event_id)
        return new_logs
    except Exception as e:
        siemplify.LOGGER.error("Error occurred while fetching logs from page {}: {}".format(page_number, e))
        return None


def create_request_body_obj(siemplify, alert_event_id, page_number=1):
    """ Creates request to send to Logz.io API """
    request_body = {}
    page_size = siemplify.extract_action_param("page_size", is_mandatory=False, default_value=DEFAULT_PAGE_SIZE, input_type=int)
    if page_size < MIN_PAGE_SIZE or page_size > MAX_PAGE_SIZE:
        siemplify.LOGGER.warn("Invalid page size. Should be betwwen {} and {}. Reverting to default page size: {}".format(MIN_PAGE_SIZE, MAX_PAGE_SIZE, DEFAULT_PAGE_SIZE))
        page_size = DEFAULT_PAGE_SIZE
    request_body["filter"] = {}
    request_body["filter"]["alertEventId"] = alert_event_id
    request_body["pagination"] = dict(pageNumber=page_number, pageSize=page_size)
    return request_body
    
    
def fetch_logs_by_event_id(api_token, req_body, url, siemplify, alert_event_id):
    """
    Returnes from Logz.io all the logs that triggered the event.
    If error occured or no results found, returnes None
    """
    headers = {
        'Content-Type': 'application/json',
        'X-API-TOKEN': api_token
    }

    siemplify.LOGGER.info("api url: {}".format(url))
    try:
        body = json.dumps(req_body)
        siemplify.LOGGER.info("Fetching logs that triggered event {} from Logz.io".format(alert_event_id))
        response = requests.post(url, headers=headers, data=body, timeout=5)
        siemplify.LOGGER.info("Status code from Logz.io: {}".format(response.status_code))
        if response.status_code == 200:
            logs_response = json.loads(response.content)
            if logs_response["total"] >= 0:
                return logs_response
            siemplify.LOGGER.warn("No resultes found to match your request")
            return None
        else:
            siemplify.LOGGER.error("API request returned {}".format(response.status_code))
    except Exception as e:
        siemplify.LOGGER.error("Error occurred while fetching logs that triggered event {} from Logz.io:\n{}".format(alert_event_id, e))
        return None
        

def get_base_api_url(region):
    """ Returnes API url, in accordance to user's input """
    if region == "us" or region == "" or region == "-":
        return BASE_URL
    else:
        return BASE_URL.replace("api.", "api-{}.".format(region))


def create_json_result(siemplify, logs_response, logzio_token, url):
    """
    This function collects all the logs that are related to the event,
    Returns the logs in json format, and the number of logs collected
    """
    collected_logs = collect_all_logs(siemplify, logs_response, logzio_token, url)
    if collected_logs is not None and len(collected_logs) >= 0:
        return json.dumps({"results": collected_logs}), len(collected_logs)
    return None


def collect_all_logs(siemplify, logs_response, api_token, url):
    """
    If there are more results than those who the first response returned,
    retrieveing the remaining logs.
    """
    collected_logs = logs_response["results"]
    num_collected_logs = len(collected_logs)
    total_results_available = int(logs_response["total"])
    current_page = int(logs_response["pagination"]["pageNumber"])
    num_pages = math.ceil(total_results_available/int(logs_response["pagination"]["pageSize"]))
    siemplify.LOGGER.info("Request retrieved {} logs from Logz.io".format(num_collected_logs))
    siemplify.LOGGER.info("There are {} logs in your Logz.io account that match your alert-event-id".format(total_results_available))
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_pages) as executor:
        futures = []
        while num_pages > current_page:
            current_page += 1
            print("fetching page: {}".format(current_page))
            futures.append(executor.submit(execute_logzio_api, siemplify, api_token, url, current_page))
        for future in concurrent.futures.as_completed(futures):
            new_log = future.result()
            if new_log is not None:
                collected_logs += new_log["results"]
                num_collected_logs += len(new_log["results"])
                siemplify.LOGGER.info("Fetched {} logs".format(len(new_log["results"])))
        
        if total_results_available != num_collected_logs:
            siemplify.LOGGER.warn("Retrieved {} logs out of {} available logs. Only the retrieved logs will be injected to Siemplify".format(num_collected_events, total_results_available))
    siemplify.LOGGER.info("Total collected: {}".format(len(collected_logs)))
    return collected_logs


def get_output_msg(status, num_logs):
    """ Returnes the output message in accordance to the script status """
    if status == EXECUTION_STATE_COMPLETED:
        return "Retrieved successfully {} logs that triggered the alert".format(num_logs)
    else:
        return "Failed to retrieve logs. Please check the script's logs to see what went wrong..."


def add_insights(siemplify, logs_json):
    try:
        logs = json.loads(logs_json)
        if len(logs["results"]) > 3:
            add_insight(siemplify, logs["results"])
        else:
            for log in logs["results"]:
                add_insight(siemplify, log)
    except Exceptions as e:
        siemplify.LOGGER.error("Error occured while trying to create insights:\n{}".format(e))


def add_insight(siemplify, log):
    try:
        alert_event_id = siemplify.extract_action_param("alert_event_id")
        severity = 0
        entity_id = ''.join([alert_event_id, datetime.datetime.now().strftime("%m%d%Y%H%M%S%f")])
        log_json = json.dumps(log)
        triggered_by = "Logzio" # Name of the integration
        title = "Logs that triggered the event"
        msg = log["message"]
        is_created = siemplify.create_case_insight(triggered_by, title, log_json, entity_id, severity, GENERAL_INSIGHT_TYPE)
        siemplify.LOGGER.info("returned value from create_case_insight: {}".format(is_created))
        return is_created
    except Exception as e:
        siemplify.LOGGER.error("Error occurred while trying to create a case insight: {}".format(e))
        return False


def get_logzio_api_endpoint(siemplify, region):
    """
    Returns the endpoint of Logz.io API.
    Prioritizing a custom endoint, if entered.
    If not, falling back to the regaular enspoints, based on the logzio_region (defaults to us).
    """
    custom_endpoint = siemplify.extract_configuration_param("Logzio", "logzio_custom_endpoint", is_mandatory=False, default_value="")
    if custom_endpoint is not None and custom_endpoint != "":
        siemplify.LOGGER.info("Using custom endpoint: {}".format(custom_endpoint))
        return custom_endpoint + SEARCH_LOGS_API_SUFFIX
    return get_base_api_url(region) + SEARCH_LOGS_API_SUFFIX

    
if __name__ == "__main__":
    main()
