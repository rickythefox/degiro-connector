# IMPORTATION STANDARD
import logging
from typing import Dict, Union

# IMPORTATION THIRD PARTY
import requests
from google.protobuf import json_format

# IMPORTATION INTERNAL
import degiro_connector.core.constants.urls as urls
from degiro_connector.core.abstracts.abstract_action import AbstractAction
from degiro_connector.trading.models.trading_pb2 import (
    Credentials,
    OrdersHistory,
)


class ActionGetOrdersHistory(AbstractAction):
    @classmethod
    def get_orders_history(
        cls,
        request: OrdersHistory.Request,
        session_id: str,
        credentials: Credentials,
        raw: bool = False,
        session: requests.Session = None,
        logger: logging.Logger = None,
    ) -> Union[dict, Update]:
        """Retrieve history about orders.
        Args:
            request (OrdersHistory.Request):
                List of options that we want to retrieve from the endpoint.
                Example :
                    from_date = OrdersHistory.Request.Date(
                        year=2020,
                        month=10,
                        day=15,
                    )
                    from_date = OrdersHistory.Request.Date(
                        year=2020,
                        month=10,
                        day=16,
                    )
                    request = OrdersHistory.Request(
                        from_date=from_date,
                        to_date=to_date,
                    )
            session_id (str):
                API's session id.
            credentials (Credentials):
                Credentials containing the parameter "int_account".
            raw (bool, optional):
                Whether are not we want the raw API response.
                Defaults to False.
            session (requests.Session, optional):
                This object will be generated if None.
                Defaults to None.
            logger (logging.Logger, optional):
                This object will be generated if None.
                Defaults to None.
        Returns:
            OrdersHistory: API response.
        """

        if logger is None:
            logger = cls.build_logger()
        if session is None:
            session = cls.build_session()

        url = urls.ORDERS_HISTORY

        params = payload_handler.orders_history_request_to_api(
            request=request,
        )
        params["intAccount"] = credentials.int_account
        params["sessionId"] = session_id

        request = requests.Request(method="GET", url=url, params=params)
        prepped = session.prepare_request(request)
        response_raw = None

        try:
            response_raw = session.send(prepped, verify=False)
            response_dict = response_raw.json()

            if raw is True:
                response = response_dict
            else:
                response = payload_handler.orders_history_to_grpc(
                    payload=response_dict,
                )
        except Exception as e:
            logger.fatal(response_raw.status_code)
            logger.fatal(response_raw.text)
            logger.fatal(e)
            return False

        return response

    def call(
        self,
        request: OrdersHistory.Request,
        raw: bool = False,
    ) -> Union[dict, OrdersHistory]:
        connection_storage = self.connection_storage
        session_id = connection_storage.session_id
        session = self.session_storage.session
        credentials = self.credentials
        logger = self.logger

        return self.get_orders_history(
            request=request,
            session_id=session_id,
            credentials=credentials,
            raw=raw,
            session=session,
            logger=logger,
        )
