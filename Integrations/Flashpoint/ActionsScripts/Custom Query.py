from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED,EXECUTION_STATE_TIMEDOUT
from FlashpointManager import FlashpointManager
import json

IDENTIFIER = u"Flash Point"
SCRIPT_NAME = "Flashpoint - Custom Query"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    
    api_key = siemplify.extract_configuration_param(IDENTIFIER,"API Key")

    query_content = siemplify.extract_action_param("Query Content")
    new_query_url = siemplify.extract_action_param("New Query URL")

    #Creating an instance of FlashPoint object
    flashpoint_manager = FlashpointManager(api_key)

    try:
        #Sending the query by the function custom_query().
        query_results = flashpoint_manager.custom_query(query_content, new_query_url)
        return_value = True
        output_message = 'The query was sent successfully'
        siemplify.result.add_result_json(query_results)
            

    except Exception as e:
        output_message = "Error fetching results from Flashpoint"
        return_value = False
        siemplify.LOGGER.error(f"Error fetching results from Flashpoint, Error: {e}.")
        siemplify.LOGGER.exception(e)
        
    
    siemplify.end(output_message, return_value)


if __name__ == "__main__":
    main()
