from dataclasses import dataclass

from SiemplifyConnectors import SiemplifyConnectorExecution

PROPERTY_KEY = "lasd_message_id"


class FetchIDError(Exception):
    """Error accessing ids"""


@dataclass
class LastMessage:
    id: str

    @classmethod
    def get(cls, siemplify: SiemplifyConnectorExecution) -> "LastMessage":
        """
        Read existing (already seen) alert id from the storage

        :param siemplify: The relevant SiemplifyConnectorExecution object
        :return:str A string describing the already seen id
        :raise FetchIDError If can't access the storage or return type doesn't match str
        """
        siemplify.LOGGER.info("Fetching existing ID AAAAAAa")
        try:
            last_saved_update_id = siemplify.get_connector_context_property(
                siemplify.context.connector_info.identifier, PROPERTY_KEY
            )
            if not isinstance(last_saved_update_id, (str, type(None))):
                raise Exception(f"Return type doesn't match. Expected: 'str', got: '{type(last_saved_update_id)}'")
        except Exception as e:
            siemplify.LOGGER.info(f"Error trying to fetch: {e}")
            raise FetchIDError(f"Can't get the last message id: {e}")
        else:
            siemplify.LOGGER.info(
                f"Last saved update id read: {last_saved_update_id}")
        return cls(last_saved_update_id)

    def save(self, siemplify: SiemplifyConnectorExecution) -> None:
        """
        Write id to the storage

        :param siemplify: The relevant SiemplifyConnectorExecution object
        """
        try:
            siemplify.set_connector_context_property(
                siemplify.context.connector_info.identifier, PROPERTY_KEY, self.id
            )
        except Exception as e:
            raise FetchIDError(f"Error trying to write the last id: {e}")
        else:
            siemplify.LOGGER.info(f"New update_id was saved: {self.id}")
