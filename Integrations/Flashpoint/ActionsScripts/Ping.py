from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED,EXECUTION_STATE_TIMEDOUT
from FlashpointManager import FlashpointManager

IDENTIFIER = u"Flash Point"

@output_handler
def main():
    siemplify = SiemplifyAction()

    api_key = siemplify.extract_configuration_param(IDENTIFIER,"API Key")

    #Creating an instance of FlashPoint object
    flashpoint_manager = FlashpointManager(api_key)
    
    #Calling the function test_connectivity() from the FlashpointManager
    response = flashpoint_manager.test_connectivity()

    if response:
        return_value = True
        output_message = 'Connected successfully'

    else:
        return_value = False
        output_message = 'The Connection failed'

    siemplify.end(output_message, return_value)


if __name__ == "__main__":
    main()
