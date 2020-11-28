import logging
import orjson as json
import onetimepass as otp
import requests
import trading.helpers.payload_handler as payload_handler
import urllib3

from trading.constants.urls import URLs
from trading.constants.headers import Headers
from trading.pb.trading_pb2 import (
    AccountOverview,
    Credentials,
    Order,
    OrdersHistory,
    ProductsLookup,
    StockList,
    TransactionsHistory,
    Update,
)
from typing import (
    List,
    Union,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def build_logger():
    return logging.getLogger(__name__)

def build_session(headers:dict=None)->requests.Session:
    """ Setup a "requests.Session" object.

    Args:
        headers (dict, optional):
            Headers to used for the Session.
            Defaults to None.

    Returns:
        requests.Session: Session object with the right headers.
    """
    

    session = requests.Session()

    if isinstance(headers, dict) :
        session.headers.update(headers)
    else:
        session.headers.update(Headers.get_headers())

    return session

def get_session_id(
    credentials:Credentials,
    session:requests.Session=None,
    logger:logging.Logger=None
)->str:
    """ Establish a connection with Degiro's Trading API.

    Args:
        credentials (Credentials):
            credentials.int_account (int)
                Account unique identifer in Degiro's system.
                It is optional.
            credentials.password (str)
                Password used to log in the website mandatory.
                It is mandatory.
            credentials.username (str)
                Username used to log in the website mandatory.
            credentials.totp_secret is optional.
                Secret code for Two-factor Authentication (2FA).
                It is optional.
        session (requests.Session, optional):
            If you one wants to reuse existing "Session" object.
            Defaults to None.
        logger (logging.Logger, optional):
            If you one wants to reuse existing "Logger" object.
            Defaults to None.

    Raises:
        ConnectionError: Connection failed.

    Returns:
        str: Session id
    """

    if logger is None:
        logger = build_logger()
    if session is None:
        session = build_session()

    if credentials.totp_secret_key:
        url = URLs.LOGIN + '/totp'
        username = credentials.username
        password = credentials.password
        totp_secret_key = credentials.totp_secret_key
        one_time_password = str(otp.get_totp(totp_secret_key))

        payload_dict = {
            'username': username,
            'password': password,
            'isPassCodeReset': False,
            'isRedirectToMobile': False,
            'queryParams': {},
            'oneTimePassword': one_time_password,
        }
    else:
        url = URLs.LOGIN
        username = credentials.username
        password = credentials.password

        payload_dict = {
            'username': username,
            'password': password,
            'isPassCodeReset': False,
            'isRedirectToMobile': False,
            'queryParams': {},
        }

    request = requests.Request(
        method='POST',
        url=url,
        json=payload_dict,
    )
    prepped = session.prepare_request(request)

    response = None
    try:
        response = session.send(prepped, verify=False)
        response_dict = response.json()
    except Exception as e:
        logger.fatal('response:%s', response)
        raise ConnectionError(e)
    
    logger.info('get_session_id:response_dict: %s', response_dict)

    if 'sessionId' in response_dict:
        return response_dict['sessionId']
    elif 'status' in response_dict and response_dict['status'] == 6:
        logger.fatal('response_dict:%s', response_dict)
        raise ConnectionError(
            '2FA is enabled, please provide the "totp_secret".'
        )
    else:
        logger.fatal('response_dict:%s', response_dict)
        raise ConnectionError('No session id returned.')
  
def get_update(
    request_list:Update.RequestList,
    session_id:str,
    credentials:Credentials,
    raw:bool=False,
    session:requests.Session=None,
    logger:logging.Logger=None,
)->Union[dict, Update]:
    """ Retrieve information from Degiro's Trading Update endpoint.

    Args:
        request (Update.RequestList):
            List of options that we want to retrieve from the endpoint.
            Example :
                request = Update.RequestList()
                request.list.extend(
                    [
                        Update.Request(
                            option=Update.Option.ALERTS,
                            last_updated=0,
                        ),
                        Update.Request(
                            option=Update.Option.CASHFUNDS,
                            last_updated=0,
                        ),
                        Update.Request(
                            option=Update.Option.HISTORICALORDERS,
                            last_updated=0,
                        ),
                        Update.Request(
                            option=Update.Option.ORDERS,
                            last_updated=0,
                        ),
                        Update.Request(
                            option=Update.Option.PORTFOLIO,
                            last_updated=0,
                        ),
                        Update.Request(
                            option=Update.Option.TOTALPORTFOLIO,
                            last_updated=0,
                        ),
                        Update.Request(
                            option=Update.Option.TRANSACTIONS,
                            last_updated=0,
                        ),
                    ]
                )
        session_id (str):
            Degiro's session id
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
        Update: API response.
    """
    
    if logger is None:
        logger = build_logger()
    if session is None:
        session = build_session()

    int_account = credentials.int_account
    url = URLs.UPDATE
    url = f'{url}/{int_account};jsessionid={session_id}'

    params = payload_handler.update_request_list_to_api(
        request_list=request_list
    )
    params['intAccount'] = int_account
    params['sessionId'] = session_id

    request = requests.Request(method='GET', url=url, params=params)
    prepped = session.prepare_request(request)
    response_raw = None

    try:
        response_raw = session.send(prepped, verify=False)
        response_dict = response_raw.json()

        if raw == True:
            response = response_dict
        else:
            response = payload_handler.build_update_from_payload(
                update_payload=response_dict,
            )
    except Exception as e:
        logger.fatal('error')
        logger.fatal(response_raw.status_code)
        logger.fatal(response_raw.text)
        logger.fatal(e)
        return False

    return response

def check_order(
    order:Order,
    session_id:str,
    credentials:Credentials,
    raw:bool=False,
    session:requests.Session=None,
    logger:logging.Logger=None,
)->Union[Order.CheckingResponse, bool]:
    if logger is None:
        logger = build_logger()
    if session is None:
        session = build_session()

    int_account = credentials.int_account
    url = URLs.ORDER_CHECK
    url = f'{url};jsessionid={session_id}?intAccount={int_account}&sessionId={session_id}'

    order_dict = {
        'buySell' : order.action,
        'orderType' : order.order_type,
        'price' : order.price,
        'productId' : order.product_id,
        'size' : order.size,
        'timeType' : order.time_type,
    }

    request = requests.Request(method='POST', url=url, json=order_dict)
    prepped = session.prepare_request(request)
    response_raw = None

    try:
        response_raw = session.send(prepped, verify=False)
        response_dict = response_raw.json()
    except Exception as e:
        logger.fatal(response_raw.status_code)
        logger.fatal(response_raw.text)
        logger.fatal(e)
        return False

    if \
        isinstance(response_dict, dict) \
        and 'data' in response_dict \
        and 'confirmationId' in response_dict['data']:

        if raw == True:
            response = response_dict
        else:
            response = payload_handler.checking_response_to_grpc(
                checking_dict=response_dict,
            )
    else:
        logger.fatal(response_raw.status_code)
        logger.fatal(response_raw.text)
        response = False

    return response

def confirm_order(
    confirmation_id:str,
    order:Order,
    session_id:str,
    credentials:Credentials,
    raw:bool=False,
    session:requests.Session=None,
    logger:logging.Logger=None,
)->Union[Order.ConfirmationResponse, bool]:
    if logger is None:
        logger = build_logger()
    if session is None:
        session = build_session()

    int_account = credentials.int_account
    url = URLs.ORDER_CONFIRM
    url = f'{url}/{confirmation_id};jsessionid={session_id}?intAccount={int_account}&sessionId={session_id}'
    
    order_dict = {
        'buySell' : order.action,
        'orderType' : order.order_type,
        'price' : order.price,
        'productId' : order.product_id,
        'size' : order.size,
        'timeType' : order.time_type,
    }

    request = requests.Request(method='POST', url=url, json=order_dict)
    prepped = session.prepare_request(request)
    response_raw = None

    try:
        response_raw = session.send(prepped, verify=False)

        response_dict = response_raw.json()
    except Exception as e:
        logger.fatal(response_raw.status_code)
        logger.fatal(response_raw.text)
        logger.fatal(e)
        return False

    if \
        isinstance(response_dict, dict) \
        and 'data' in response_dict \
        and 'orderId' in response_dict['data']:

        if raw == True:
            order.id = response_dict['data']['orderId']
            response = response_dict
        else:
            order.id = response_dict['data']['orderId']
            response = payload_handler.confirmation_response_to_grpc(
                confirmation_dict=response_dict,
            )
    else:
        response = False

    return response

def update_order(
    order:Order,
    session_id:str,
    credentials:Credentials,
    raw:bool=False,
    session:requests.Session=None,
    logger:logging.Logger=None,
)->bool:
    if logger is None:
        logger = build_logger()
    if session is None:
        session = build_session()

    int_account = credentials.int_account
    order_id = order.id
    url = URLs.ORDER_UPDATE
    url = f'{url}/{order_id};jsessionid={session_id}?intAccount={int_account}&sessionId={session_id}'

    order_dict = {
        'buySell' : order.action,
        'orderType' : order.order_type,
        'price' : order.price,
        'productId' : order.product_id,
        'size' : order.size,
        'timeType' : order.time_type,
    }

    request = requests.Request(method='PUT', url=url, json=order_dict)
    prepped = session.prepare_request(request)
    response = None

    try:
        response = session.send(prepped, verify=False)
    except Exception as e:
        logger.fatal(response.status_code)
        logger.fatal(response.text)
        logger.fatal(e)
        return False

    return response.status_code == 200

def delete_order(
    order_id:str,
    session_id:str,
    credentials:Credentials,
    raw:bool=False,
    session:requests.Session=None,
    logger:logging.Logger=None,
)->bool:
    if logger is None:
        logger = build_logger()
    if session is None:
        session = build_session()

    int_account = credentials.int_account
    url = URLs.ORDER_DELETE
    url = f'{url}/{order_id};jsessionid={session_id}?intAccount={int_account}&sessionId={session_id}'

    request = requests.Request(method='DELETE', url=url)
    prepped = session.prepare_request(request)
    response = None

    try:
        response = session.send(prepped, verify=False)
        response = response.json()
    except Exception as e:
        logger.fatal(response.status_code)
        logger.fatal(response.text)
        logger.fatal(e)
        return False
    
    return  response.status_code == 200

def get_config(
    session_id:str,
    session:requests.Session=None,
    logger:logging.Logger=None,
)->dict:
    if logger is None:
        logger = build_logger()
    if session is None:
        session = build_session()
    
    url = URLs.CONFIG

    request = requests.Request(method='GET', url=url)
    prepped = session.prepare_request(request)
    prepped.headers['cookie'] = 'JSESSIONID=' + session_id

    try:
        response = session.send(prepped, verify=False)
        response = response.json()
    except Exception as e:
        logger.fatal(e)
        return False

    if (
        type(response) != dict
        or 'data' not in response
    ): return False

    return response['data']


def get_client_details(
    session_id:str,
    session:requests.Session=None,
    logger:logging.Logger=None,
)->dict:
    if logger is None:
        logger = build_logger()
    if session is None:
        session = build_session()
    
    url = f'{URLs.CLIENT_DETAILS}?sessionId={session_id}'
    
    request = requests.Request(method='GET', url=url)
    prepped = session.prepare_request(request)
    response = session.send(prepped, verify=False)

    if response.status_code != 200: return False
    
    response_payload = response.json()

    if (
        type(response_payload) != dict
        or 'data' not in response_payload
    ): return False

    return response_payload

def get_client_info(
    session_id:str,
    credentials:Credentials,
    session:requests.Session=None,
    logger:logging.Logger=None,
)->dict:
    if logger is None:
        logger = build_logger()
    if session is None:
        session = build_session()

    int_account = credentials.int_account
    url = f'{URLs.CLIENT_INFO}/{int_account};jsessionid={session_id}'
    
    request = requests.Request(method='GET', url=url)
    prepped = session.prepare_request(request)
    response = session.send(prepped, verify=False)
    
    if response.status_code != 200: return False

    return response.text

def get_orders_history(
    request:OrdersHistory.Request,
    session_id:str,
    credentials:Credentials,
    raw:bool=False,
    session:requests.Session=None,
    logger:logging.Logger=None,
)->Union[dict, Update]:
    """ Retrieve history about orders.

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
            Degiro's session id
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
        logger = build_logger()
    if session is None:
        session = build_session()

    url = URLs.ORDERS_HISTORY

    params = payload_handler.orders_history_request_to_api(
        request=request,
    )
    params['intAccount'] = credentials.int_account
    params['sessionId'] = session_id

    request = requests.Request(method='GET', url=url, params=params)
    prepped = session.prepare_request(request)
    response_raw = None

    try:
        response_raw = session.send(prepped, verify=False)
        response_dict = response_raw.json()

        if raw == True:
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

def get_transactions_history(
    request:TransactionsHistory.Request,
    session_id:str,
    credentials:Credentials,
    raw:bool=False,
    session:requests.Session=None,
    logger:logging.Logger=None,
)->Union[dict, Update]:
    """ Retrieve history about transactions.

    Args:
        request (TransactionsHistory.Request):
            List of options that we want to retrieve from the endpoint.
            Example :
                from_date = TransactionsHistory.Request.Date(
                    year=2020,
                    month=10,
                    day=15,
                )
                from_date = TransactionsHistory.Request.Date(
                    year=2020,
                    month=10,
                    day=16,
                )
                request = TransactionsHistory.Request(
                    from_date=from_date,
                    to_date=to_date,
                )
        session_id (str):
            Degiro's session id
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
        TransactionsHistory: API response.
    """
    
    if logger is None:
        logger = build_logger()
    if session is None:
        session = build_session()

    url = URLs.TRANSACTIONS_HISTORY

    params = payload_handler.transactions_history_request_to_api(
        request=request
    )
    params['intAccount'] = credentials.int_account
    params['sessionId'] = session_id

    request = requests.Request(method='GET', url=url, params=params)
    prepped = session.prepare_request(request)
    response_raw = None

    try:
        response_raw = session.send(prepped, verify=False)
        response_dict = response_raw.json()

        if raw == True:
            response = response_dict
        else:
            response = payload_handler.transactions_history_to_grpc(
                payload=response_dict,
            )
    except Exception as e:
        logger.fatal(response_raw.status_code)
        logger.fatal(response_raw.text)
        logger.fatal(e)
        return False

    return response

def get_account_overview(
    request:AccountOverview.Request,
    session_id:str,
    credentials:Credentials,
    raw:bool=False,
    session:requests.Session=None,
    logger:logging.Logger=None,
)->Union[dict, Update]:
    """ Retrieve information about the account.

    Args:
        request (AccountOverview.Request):
            List of options that we want to retrieve from the endpoint.
            Example :
                from_date = AccountOverview.Request.Date(
                    year=2020,
                    month=10,
                    day=15,
                )
                from_date = AccountOverview.Request.Date(
                    year=2020,
                    month=10,
                    day=16,
                )
                request = AccountOverview.Request(
                    from_date=from_date,
                    to_date=to_date,
                )
        session_id (str):
            Degiro's session id
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
        AccountOverview: API response.
    """
    
    if logger is None:
        logger = build_logger()
    if session is None:
        session = build_session()

    url = URLs.ACCOUNT_OVERVIEW
    params = payload_handler.account_overview_request_to_api(
        request=request
    )
    params['intAccount'] = credentials.int_account
    params['sessionId'] = session_id

    request = requests.Request(method='GET', url=url, params=params)
    prepped = session.prepare_request(request)
    response_raw = None

    try:
        response_raw = session.send(prepped, verify=False)
        response_dict = response_raw.json()

        if raw == True:
            response = response_dict
        else:
            response = payload_handler.account_overview_to_grpc(
                payload=response_dict,
            )
    except Exception as e:
        logger.fatal(response_raw.status_code)
        logger.fatal(response_raw.text)
        logger.fatal(e)
        return False

    return response

def products_lookup(
    request:ProductsLookup.Request,
    session_id:str,
    credentials:Credentials,
    raw:bool=False,
    session:requests.Session=None,
    logger:logging.Logger=None,
)->Union[dict, ProductsLookup]:
    """ Retrieve information about the account.

    Args:
        request (ProductsLookup.Request):
            List of options that we want to retrieve from the endpoint.
            Example :
                request = ProductsLookup.Request(
                    search_text='APPLE',
                    limit=10,
                    offset=0,
                )
        session_id (str):
            Degiro's session id
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
        AccountOverview: API response.
    """
    
    if logger is None:
        logger = build_logger()
    if session is None:
        session = build_session()

    url = URLs.PRODUCTS_LOOKUP

    params = payload_handler.products_loopkup_request_to_grpc(
        request=request
    )
    params['intAccount'] = credentials.int_account
    params['sessionId'] = session_id

    request = requests.Request(method='GET', url=url, params=params)
    prepped = session.prepare_request(request)
    response_raw = None

    try:
        response_raw = session.send(prepped, verify=False)
        response_dict = response_raw.json()

        if raw == True:
            response = response_dict
        else:
            response = payload_handler.products_loopkup_to_grpc(
                payload=response_dict,
            )
    except Exception as e:
        logger.fatal(response_raw.status_code)
        logger.fatal(response_raw.text)
        logger.fatal(e)
        return False

    return response

def get_stock_list(
    request:StockList.Request,
    session_id:str,
    credentials:Credentials,
    raw:bool=False,
    session:requests.Session=None,
    logger:logging.Logger=None,
)->Union[dict, StockList]:
    """ Retrieve information about the account.

    Args:
        request (StockList.Request):
            List of options that we want to retrieve from the endpoint.
            Example :
                request = StockList.Request(
                    indexId=5,
                    isInUSGreenList=False,
                    limit=100,
                    offset=0,
                    requireTotal=True,
                    sortColumns='name',
                    sortTypes='asc',
                    stockCountryId=886,
                )
        session_id (str):
            Degiro's session id
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
        AccountOverview: API response.
    """
    
    if logger is None:
        logger = build_logger()
    if session is None:
        session = build_session()

    url = URLs.STOCK_LIST

    params = payload_handler.stock_list_request_to_grpc(
        request=request
    )
    params['intAccount'] = credentials.int_account
    params['sessionId'] = session_id

    request = requests.Request(method='GET', url=url, params=params)
    prepped = session.prepare_request(request)
    response_raw = None

    try:
        response_raw = session.send(prepped, verify=False)
        response_dict = response_raw.json()

        if raw == True:
            response = response_dict
        else:
            response = payload_handler.stock_list_to_grpc(
                payload=response_dict,
            )
    except Exception as e:
        logger.fatal(response_raw.status_code)
        logger.fatal(response_raw.text)
        logger.fatal(e)
        return False

    return response

if __name__ == '__main__':
    # IMPORTATIONS
    import json
    import logging

    from trading.pb.trading_pb2 import Credentials

    # FETCH CONFIG
    with open('config.json') as config_file:
        config = json.load(config_file)
    
    # SETUP CREDENTIALS
    username = config['username']
    password = config['password']
    int_account = config['int_account']
    credentials = Credentials(
        int_account=int_account,
        username=username,
        password=password
    )

    # SETUP LOGS
    log_level = logging._nameToLevel['INFO']
    log_level = logging.getLevelName(log_level)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        filename='test2.log',
    )
    logger = logging.getLogger(__name__)

    # SETUP SESSION
    headers = Headers.get_headers()
    session = build_session(headers=headers)

    # ESTABLISH CONNECTION
    session_id = get_session_id(
        credentials=credentials,
        session=session,
        logger=logger,
    )