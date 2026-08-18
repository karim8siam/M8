"""
Matrix8 BSC On-Chain Blockchain Verifier
Verifies Binance Smart Chain (BSC - BEP20) USDT transfers to the System Treasury.
Contract: BSC USDT (0x55d398326f99059fF775485246999027B3197955)
Treasury: 0x9ff36bB1b16F1421b2CeBFFE311aCB8D5800AE43
"""

import json
import urllib.request
import ssl

BSC_RPC_ENDPOINTS = [
    'https://bsc-dataseed.binance.org/',
    'https://bsc-dataseed1.defibit.io/',
    'https://bsc-dataseed2.binance.org/',
    'https://rpc.ankr.com/bsc'
]

BSC_USDT_CONTRACT = '0x55d398326f99059ff775485246999027b3197955'.lower()
SYSTEM_TREASURY = '0x9ff36bB1b16F1421b2CeBFFE311aCB8D5800AE43'.lower()
TRANSFER_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'.lower()
REQUIRED_USDT_AMOUNT = 3.40

def rpc_call(method, params):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }
    data = json.dumps(payload).encode('utf-8')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for endpoint in BSC_RPC_ENDPOINTS:
        try:
            req = urllib.request.Request(
                endpoint,
                data=data,
                headers={'Content-Type': 'application/json', 'User-Agent': 'Matrix8/1.0'}
            )
            with urllib.request.urlopen(req, context=ctx, timeout=8) as response:
                res = json.loads(response.read().decode('utf-8'))
                if 'result' in res:
                    return res['result']
        except Exception as e:
            continue
    return None

def normalize_address(hex_str):
    if not hex_str:
        return ''
    clean = hex_str.lower()
    if clean.startswith('0x'):
        clean = clean[2:]
    if len(clean) > 40:
        clean = clean[-40:]
    return '0x' + clean

def verify_bsc_deposit(tx_hash, expected_sender_wallet=None):
    """
    Verifies on-chain if tx_hash is a confirmed BSC USDT transfer to SYSTEM_TREASURY for >= 3.40 USDT.
    Returns dict with verification results.
    """
    tx_hash = tx_hash.strip()
    if not tx_hash.startswith('0x') or len(tx_hash) != 66:
        return {
            'verified': False,
            'error': 'Invalid BSC Transaction Hash format (Must be 66 chars starting with 0x)'
        }

    # Query Receipt from BSC
    receipt = rpc_call('eth_getTransactionReceipt', [tx_hash])
    if not receipt:
        return {
            'verified': False,
            'error': 'Transaction not found on BSC network yet. Please wait a few seconds and try again.'
        }

    # Check status == 0x1 (Success)
    status = receipt.get('status')
    if status != '0x1':
        return {
            'verified': False,
            'error': 'Transaction failed or reverted on Binance Smart Chain.'
        }

    logs = receipt.get('logs', [])
    valid_transfer = None

    for log in logs:
        log_contract = log.get('address', '').lower()
        topics = log.get('topics', [])
        
        if len(topics) >= 3 and topics[0].lower() == TRANSFER_TOPIC:
            from_addr = normalize_address(topics[1])
            to_addr = normalize_address(topics[2])
            data = log.get('data', '0x0')
            try:
                raw_amount = int(data, 16)
                # BSC USDT has 18 decimals
                amount_usdt = raw_amount / (10 ** 18)
            except Exception:
                continue

            # Check if sent to Treasury
            if to_addr == SYSTEM_TREASURY:
                # Check contract is BSC USDT
                if log_contract == BSC_USDT_CONTRACT:
                    if amount_usdt >= REQUIRED_USDT_AMOUNT - 0.001:
                        valid_transfer = {
                            'contract': log_contract,
                            'from_wallet': from_addr,
                            'to_wallet': to_addr,
                            'amount_usdt': amount_usdt,
                            'block_number': int(receipt.get('blockNumber', '0x0'), 16),
                            'tx_hash': tx_hash
                        }
                        break

    if not valid_transfer:
        return {
            'verified': False,
            'error': f'No confirmed 3.40 USDT transfer found to Treasury ({SYSTEM_TREASURY[:10]}...).'
        }

    # Verified on BSC Mainnet
    return {
        'verified': True,
        'details': valid_transfer
    }

def find_bsc_deposit_by_sender(sender_wallet, max_blocks=300):
    """
    Scans recent BSC blocks for an incoming USDT transfer from sender_wallet to SYSTEM_TREASURY.
    Returns the verified transaction hash and details if found.
    """
    if not sender_wallet:
        return None
    
    sender_clean = sender_wallet.strip().lower()
    if not sender_clean.startswith('0x') or len(sender_clean) != 42:
        return None

    # Get latest block number
    block_hex = rpc_call('eth_blockNumber', [])
    if not block_hex:
        return None
    
    try:
        latest_block = int(block_hex, 16)
        from_block = hex(max(0, latest_block - max_blocks))
    except Exception:
        from_block = 'latest'

    padded_sender = '0x000000000000000000000000' + sender_clean[2:]
    padded_treasury = '0x000000000000000000000000' + SYSTEM_TREASURY[2:]

    logs = rpc_call('eth_getLogs', [{
        'address': BSC_USDT_CONTRACT,
        'topics': [TRANSFER_TOPIC, padded_sender, padded_treasury],
        'fromBlock': from_block,
        'toBlock': 'latest'
    }])

    if not logs or not isinstance(logs, list):
        return None

    for log in reversed(logs):
        tx_hash = log.get('transactionHash')
        data = log.get('data', '0x0')
        try:
            raw_amount = int(data, 16)
            amount_usdt = raw_amount / (10 ** 18)
        except Exception:
            continue

        if amount_usdt >= REQUIRED_USDT_AMOUNT - 0.001:
            return {
                'tx_hash': tx_hash,
                'amount_usdt': amount_usdt,
                'block_number': int(log.get('blockNumber', '0x0'), 16),
                'from_wallet': sender_clean,
                'to_wallet': SYSTEM_TREASURY
            }
    
    return None
