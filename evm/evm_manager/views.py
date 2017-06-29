from django.http import JsonResponse
from rest_framework.views import APIView
from evm_manager.models import StateInfo
from evm_manager import evm_singleton
from gcoinbackend import core as gcoincore

import requests
try:
    import http.client as httplib
except ImportError:
    import httplib


def error_response(**kwargs):
    response, error, data = {}, [], {}
    for k, v in kwargs.items():
        data[k] = v
    error.append(data)
    response['errors'] = error
    return response


def std_response(**kwargs):
    response, data = {}, {}
    for k, v in kwargs.items():
        data[k] = v
    response['data'] = data
    return response


class CheckState(APIView):
    http_method_name = ['get']

    def get(self, request, multisig_address, tx_hash):
        try:
            contract_address = []
            completed = evm_singleton.check_state(multisig_address, tx_hash)
            if completed:
                try:
                    contract_address = evm_singleton.read_tx_result_file('0x'+tx_hash)
                except:
                    print("failed to read the transaction result file")
                response = std_response(completed=completed, contract_address=contract_address)
            else:
                response = std_response(completed=completed)
            return JsonResponse(response, status=httplib.OK)
        except Exception as e:
            response = std_response(completed=False)
            return JsonResponse(response, status=httplib.OK)
