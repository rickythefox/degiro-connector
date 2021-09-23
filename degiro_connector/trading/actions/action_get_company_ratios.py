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
    CompanyRatios,
)


class ActionGetCompanyRatios(AbstractAction):
    @classmethod
    def get_company_ratios(
        cls,
        product_isin: str,
        session_id: str,
        credentials: Credentials,
        raw: bool = False,
        session: requests.Session = None,
        logger: logging.Logger = None,
    ) -> Union[dict, CompanyRatios]:
        if logger is None:
            logger = cls.build_logger()
        if session is None:
            session = cls.build_session()

        int_account = credentials.int_account
        url = f"{urls.COMPANY_RATIOS}/{product_isin}"

        params = {
            "intAccount": int_account,
            "sessionId": session_id,
        }

        request = requests.Request(method="GET", url=url, params=params)
        prepped = session.prepare_request(request)
        prepped.headers["cookie"] = "JSESSIONID=" + session_id

        response_raw = None

        try:
            response_raw = session.send(prepped, verify=False)
            response_dict = response_raw.json()

            if raw is True:
                response = response_dict
            else:
                response = cls.company_ratios_to_grpc(
                    payload=response_dict,
                )
        except Exception as e:
            logger.fatal("error")
            logger.fatal(response_raw.status_code)
            logger.fatal(response_raw.text)
            logger.fatal(e)
            return False

        return response

    def call(
        self,
        product_isin: str,
        raw: bool = False,
    ) -> Union[dict, CompanyRatios]:
        connection_storage = self.connection_storage
        session_id = connection_storage.session_id
        session = self.session_storage.session
        credentials = self.credentials
        logger = self.logger

        return self.get_company_ratios(
            product_isin=product_isin,
            session_id=session_id,
            credentials=credentials,
            raw=raw,
            session=session,
            logger=logger,
        )
