from gcoinapi.client import GcoinAPIClient
from django.conf import settings
from django.db import transaction
from .models import StateInfo
from .utils import (get_multisig_address, get_tx_info, get_sender_address, 
                    wallet_address_to_evm, make_contract_address)
from threading import Lock
from .evm_singleton import (run_evm, write_state, read_state, delete_state, 
                            init_state, write_log_file, backup_state, read_log_file, 
                            call_const_func)
from .exceptions import DoubleSpendingError, UnsupportedTxTypeError
import json
import logging

LOG_FILE_FORMAT = '{multisig_address}_{tx_hash}_log'
BACKUP_FILE_FORMAT = '{multisig_address}_{tx_hash}_{sequence}'
CONTRACT_FEE_COLOR = 1
CONTRACT_FEE_AMOUNT = 100000000
LOCK_POOL_SIZE = 64
LOCKS = [Lock() for i in range(LOCK_POOL_SIZE)]
logger = logging.getLogger(__name__)
OSSclient = GcoinAPIClient(settings.OSS_API_URL)

def deploy_contracts(tx_hash):
    """
    """
    logger.info('---------- Start  updating ----------')
    logger.info('/notify/' + tx_hash)

    tx = OSSclient.get_tx(tx_hash)
    multisig_address = get_multisig_address(tx)
    if tx['type'] == 'NORMAL' and multisig_address is None:
        raise UnsupportedTxTypeError
    """
    avoid the same multisig address execute the transaction
    we use a lock for multisig address
    """
    lock = get_lock(multisig_address)
    with lock:
        txs, latest_tx_hash = get_unexecuted_txs(multisig_address, tx_hash, tx['time'])

        logger.info('Start : The latest updated tx of ' + multisig_address + ' is ' + (latest_tx_hash or 'None'))
        logger.info(str(len(txs)) + ' non-updated txs are found')

        for i, tx in enumerate(txs):
            logger.info(str(i+1) + '/' + str(len(txs)) + ' updating tx: ' + tx['type'] + ' ' + tx['hash'])
            
            deploy_single_tx(tx, latest_tx_hash, multisig_address)

            latest_tx_hash = tx['hash']

        logger.info('Finish: The latest updated tx is ' + (latest_tx_hash or 'None'))
        logger.info('---------- Finish updating ----------')
        return True

def get_lock(multisig_address):
    index = abs(hash(str(multisig_address))) % LOCK_POOL_SIZE
    return LOCKS[index]

def get_unexecuted_txs(multisig_address, tx_hash, _time):
    state, created = StateInfo.objects.get_or_create(multisig_address=multisig_address)
    latest_tx_time = int(state.latest_tx_time or 0)
    latest_tx_hash = state.latest_tx_hash

    if int(_time) < int(latest_tx_time):
        return [], latest_tx_hash
    page, txs = OSSclient.get_txs_by_address(multisig_address, starting_after=None, since=latest_tx_time, tx_type=None)
    txs = txs[::-1]
    if latest_tx_time == 0:
        return txs, latest_tx_hash
    for i, tx in enumerate(txs):
        if tx.get('hash') == latest_tx_hash:
            return txs[i + 1:], latest_tx_hash

@transaction.atomic
def deploy_single_tx(tx, ex_tx_hash, multisig_address):
    tx_info = get_tx_info(tx)
    sender_address = get_sender_address(tx)
    tx_hash, _time = tx['hash'], tx['time']
    state, created = StateInfo.objects.get_or_create(multisig_address=multisig_address)
    if tx['type'] == 'CONTRACT':
        command, contract_address, is_deploy = get_command(tx_info, sender_address)
        run_evm(command)
        inc_nonce(multisig_address, sender_address)
        state.latest_tx_hash = tx_hash
        state.latest_tx_time = _time
        state.save()
    elif tx['type'] == 'NORMAL' and sender_address == multisig_address:
        content = read_state(multisig_address)
        content = get_remaining_money(content, tx_info, multisig_address)
        write_state(multisig_address, content)
    else:
        logger.info('Ignored: non-contract & non-cashout type ' + tx_info['hash'])

def get_command(tx_info, sender_address):
    _time = tx_info['time']
    bytecode = tx_info['op_return']['bytecode']
    is_deploy = tx_info['op_return']['is_deploy']
    multisig_address = tx_info['op_return']['multisig_address']
    contract_address = tx_info['op_return']['contract_address']
    value = get_value(tx_info, multisig_address)
    sender_hex = wallet_address_to_evm(sender_address)
    command = "--sender " + sender_hex + \
        " --fund " + "'" + value + "'" + \
        " --value " + "'" + value + "'" + \
        " --multisig " + multisig_address + \
        " --time " + str(_time)
    if is_deploy:
        contract_address = make_contract_address(multisig_address, sender_address)
        command = command + \
            " --receiver " + contract_address + \
            " --code " + bytecode + \
            " --deploy "
    else:
        command = command + \
            " --receiver " + contract_address + \
            " --input " + bytecode
    return command, contract_address, is_deploy

def inc_nonce(multisig_address, sender_address):
    sender_evm_address = wallet_address_to_evm(sender_address)
    command = '--multisig ' + multisig_address + ' --inc --receiver ' + sender_evm_address
    run_evm(command)

def get_value(tx_info, multisig_address):
    value = {}
    for vout in tx_info['vouts']:
        if(vout['address'] == multisig_address):
            value[vout['color']] = value.get(vout['color'], 0) + int(vout['amount'])
    value[CONTRACT_FEE_COLOR] -= CONTRACT_FEE_AMOUNT
    for v in value:
        value[v] = str(value[v] / 100000000)
    return "".join(json.dumps(value).split())

def get_remaining_money(content, tx_info, multisig_address):
    for vout in tx_info['vouts']:
        output_address = vout['address']
        output_color = vout['color']
        # convert to diqi
        output_amount = vout['amount'] / 100000000

        if output_address == multisig_address:
            continue
        output_evm_address = wallet_address_to_evm(output_address)
        account = None
        if output_evm_address in content['accounts']:
            account = content['accounts'][output_evm_address]
        if not account:
            raise DoubleSpendingError
        amount = account['balance'][str(output_color)]
        if not amount:
            raise DoubleSpendingError
        if int(amount) < int(output_amount):
            raise DoubleSpendingError

        amount = str(int(amount) - int(output_amount))
        content['accounts'][output_evm_address]['balance'][str(output_color)] = amount
    return content

def make_multisig_address_file(multisig_address):
    init_state(multisig_address)

def call_constant_function(sender_address, multisig_address, byte_code, value, contract_address):
    sender_evm_address = wallet_address_to_evm(sender_address)
    return call_const_func(multisig_address, byte_code, contract_address, sender_evm_address)
