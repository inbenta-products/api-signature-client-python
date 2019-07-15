# -*- coding: utf-8 -*-
try:
    from requests.adapters import HTTPAdapter
    BUILD_ADAPTER = True
except ImportError:
    BUILD_ADAPTER = False

from .protocol import *

from .__version__ import __title__, __description__, __url__, __version__
from .__version__ import __author__, __author_email__, __license__
from .__version__ import __copyright__

__all__ = ['SignatureClient']

class SignatureClient(object):
    '''Inbenta Signature Client

    This client allows to sign a request and validate the response,
    the sign request will generate the headers to make the requests.

    Args:
        signatureKey (str): The Inbenta signature key that will be used
        baseUrl (str, optional): The base endpoint url
        signatureVersion (str, optional): signature protocol version (default: lastest)
    
    Raises:
        TypeError: if the signature version is not suported
    '''
    def __init__(self, signatureKey, baseUrl=None, signatureVersion=None):
        signatureVersion = signatureVersion or "v1"
        if not isinstance(signatureVersion, BaseVersion):
            signatureVersion = {
                "v1": V1(signatureKey, baseUrl=baseUrl)
            }.get(str(signatureVersion).lower())
        if not signatureVersion:
            raise ValueError('Signature Version is not correct. Supported versions: [v1]')
        self._signProtocol = signatureVersion

    @property
    def SIGNATURE_HEADER(self):
        return self._signProtocol.SIGNATURE_HEADER

    def genTimestamp(self):
        '''Generates a timestamp in string format for the request'''
        return self._signProtocol.genTimestamp()

    def signRequest(self, url, params=None, body=None, method=None, timestamp=None):
        '''Build the signature headers

        Args:
            url (str): The endpoint url (can contain encoded query parameters)
            params (dict): The query parameters without encoding
            body (string): The body of the request
            method (string): The HTTP Method
            timestamp (str, optional): timestamp to be used

        Return:
            dict: The signature headers generated by the requests

        '''
        signature = self._signProtocol.signRequest(url=url, method=method, params=params, body=body, timestamp=timestamp)
        return self._signProtocol.getHeaders(signature)

    def validateResponse(self, signature, body, timestamp=None):
        '''Validate the signature header of the response

        Args:
            signature (str): The signature header of the response
            body (str): The response body
            timestamp (str, optional): timestamp to be used

        Return:
            bool: True or False if signature could be verified or not

        '''
        return self._signProtocol.validateResponse(signature=signature, body=body, timestamp=timestamp)


if BUILD_ADAPTER:
    __all__ += ['SignatureAdapter', 'changeBaseHTTPAdapter', 'getHTTPAdapter']

    def __createAdapter(cls):
        class SignatureAdapter(cls):
            '''Requests HTTP Adapter to sign the request

            The adapter will sign the request and add the headers before making the request
            Also will validate the signature on the response.

            On the response a new attribute is added `validSignature` this attribute will be
                None:  If the signature wasn't provided
                True:  The response signature is valid
                False:  The response signature doesn't match

            Args:
                signatureKey (str): Inbenta signature key
                signatureVersion (str, optional): signature protocol version (default: lastest)
                *args: list args that will be passed to the parent HTTPAdapter
                **kwargs: list of kwargs that will be passed to the parent HTTPAdapter

            Example:
                import requests
                s = requests.Session()
                s.mount(INBNETA_ENDPOINT_URL, SignatureAdapter(INBENTA_SIGNATURE_KEY))
                ...
                r = s.get(url)
                ...
                r.validSignature

            '''
            def __init__(self, signatureKey, baseUrl=None, signatureVersion=None, *args, **kwargs):
                super(SignatureAdapter, self).__init__(*args, **kwargs)
                self._client = SignatureClient(signatureKey, signatureVersion=signatureVersion, baseUrl=baseUrl)
                self._timestamp = None

            def add_headers(self, request, **kwargs):
                self._timestamp = self._client.genTimestamp()
                headers = self._client.signRequest(url=request.url, method=request.method, body=request.body, timestamp=self._timestamp)
                request.headers.update(headers)

            def build_response(self, req, resp):
                response = super(SignatureAdapter, self).build_response(req, resp)
                signature = response.headers.get(self._client.SIGNATURE_HEADER)
                response.validSignature = None
                if signature:
                    response.validSignature = self._client.validateResponse(signature, response.text, timestamp=self._timestamp)
                return response
        return SignatureAdapter

    def changeBaseHTTPAdapter(cls):
        '''Allows to change the base class of the Adapter to use a custom HTTPAdapter'''
        if not isinstance(cls, type) or not issubclass(cls, HTTPAdapter):
            raise TypeError("The adapter class should be an class of type HTTPAdapter")
        global SignatureAdapter
        SignatureAdapter = __createAdapter(cls)
        return SignatureAdapter

    SignatureAdapter = __createAdapter(HTTPAdapter)