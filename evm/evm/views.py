try:
    import http.client as httplib
except ImportError:
    import httplib
from rest_framework.views import APIView

from evm_manager import deploy_contract_utils

from evm import ERROR_CODE, error_response, data_response

import threading

def evm_deploy(tx_hash):
    print('Deploy tx_hash ' + tx_hash)
    completed = deploy_contract_utils.deploy_contracts(tx_hash)
    if completed:
        print('Deployed Success')
    else:
        print('Deployed Failed')
    #
    # Cash out function
    # Modified in future
    # multisig_address = deploy_contract_utils.get_multisig_address(tx_hash)
    # response = clear_evm_accounts(multisig_address)

def make_multisig_address_file(multisig_address):
    deploy_contract_utils.make_multisig_address_file(multisig_address)

class TxDeploy(APIView):
    @handle_uncaught_exception
    def post(self, request, tx_hash):
        response = {"message": 'Start to deploy tx_hash ' + tx_hash}
        t = threading.Thread(target=evm_deploy, args=[tx_hash, ])
        t.start()
        return data_response(response)


class MultisigDeploy(APIView):
    """
    make a multisig address file
    """
    @handle_uncaught_exception
    def post(self, request, multisig_address):
        response = {"message": 'Start to make a multisig address file'}
        t = threading.Thread(target=make_multisig_address_file, args=[multisig_address, ])
        t.start()
        return data_response(response)


class CallConstantFunction(APIView):
    """
    call constant function
    """
    @handle_uncaught_exception
    def post(self, request):
        
        data = deploy_contract_utils.call_constant_function(
                    sender_address, multisig_address, evm_input_code, amount, contract_address)
        response = {"message": 'Start to make a multisig address file'}
        return data_response(response)
