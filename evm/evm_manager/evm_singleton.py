from subprocess import check_output
from django.conf import settings
import logging
import json
evm_daemon_settings = getattr(settings, 'EVM_DAEMON_SETTINGS')
logger = logging.getLogger(__name__)
_CALLER = None


class Caller(object):
    def __init__(self, path=evm_daemon_settings['CALLER'], ipc=evm_daemon_settings['IPC']):
        self.path = path
        self.ipc = ipc

    def run(self, args):
        args = self.path + ' --ipc ' + self.ipc + ' ' + args
        logger.debug(args)
        arr = []
        args = args.split("'")
        for a in args:
            if '{' in a:
                arr = arr + [a]
            else:
                arr = arr + a.split()
        return check_output(arr, shell=False)


def get_evm_caller():
    global _CALLER
    if not _CALLER:
        _CALLER = Caller()
    return _CALLER


def run_evm(command):
    caller = get_evm_caller()
    return caller.run(command)


def write_log_file(multisig_address, filename):
    filepath = evm_daemon_settings['LOG_DIR'] + filename
    command = '--multisig ' + multisig_address + ' --writelog ' + filepath
    run_evm(command)


def read_log_file(multisig_address, filename):
    filepath = evm_daemon_settings['LOG_DIR'] + filename
    with open(filepath, 'r') as f:
        content = json.load(f)
    return content


def write_state(multisig_address, content, account=None):
    with open(evm_daemon_settings['TMP_DIR'] + multisig_address, 'w') as f:
        json.dump(content, f, sort_keys=True, indent=4, separators=(',', ': '))
    command = '--multisig ' + multisig_address + ' --writestate ' + evm_daemon_settings['TMP_DIR'] + multisig_address
    run_evm(command)


def delete_state(multisig_address):
    command = '--multisig ' + multisig_address + ' --remove'
    run_evm(command)


def read_state(multisig_address, account=None):
    command = '--multisig ' + multisig_address + ' --dump'
    try:
        content = run_evm(command).decode('utf-8')
        return json.loads(content)
    except:
        return {}


def backup_state(multisig_address, filename):
    content = read_state(multisig_address)
    filepath = evm_daemon_settings['BACKUP_DIR'] + filename
    with open(filepath, 'w') as f:
        json.dump(content, f, sort_keys=True, indent=4, separators=(',', ': '))


def read_backup_file(filename):
    filepath = evm_daemon_settings['BACKUP_DIR'] + filename
    with open(filepath, 'r') as f:
        content = json.load(f)
    return content


def init_state(multisig_address):
    command = '--multisig ' + multisig_address + ' --deploy'
    run_evm(command)


def call_const_func(multisig_address, code, contract_address, sender_evm_address):
    command = '--sender {sender} --multisig {multisig} --input {code} --receiver {receiver} --return'.format(
        sender=sender_evm_address, multisig=multisig_address, code=code, receiver=contract_address)
    out = run_evm(command)
    return {'out': out.decode().split()[-1]}


def check_state(multisig_address, tx_hash):
    command = '--multisig ' + multisig_address + ' --txhash ' + tx_hash + ' --check'
    out = run_evm(command)
    out = out.decode().split()[-1]
    if out == 'true':
        return True
    else:
        return False

def read_tx_result_file(filename):
    filepath = evm_daemon_settings['TX_RESULT_DIR'] + filename
    contract_address = []
    with open(filepath, 'r') as f:
        for line in f:
            words = line.split()
            if words[-1] == 'true':
                contract_address.append(words[3])
    return contract_address
