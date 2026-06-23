# -*- coding: utf-8 -*-
# Part of Creyox Technologies
from odoo import http
from odoo.http import request
import requests
from urllib.parse import parse_qs
import logging

_logger = logging.getLogger(__name__)


class NMIController(http.Controller):

    @http.route('/pos/nmi/payment/initiate', type='json', auth='public', methods=['POST'])
    def nmi_payment_initiate(self, **kwargs):
        """Initiate an asynchronous transaction on the POI device."""
        try:
            payment_method_id = kwargs.get('payment_method_id')
            amount = kwargs.get('amount')
            reference = kwargs.get('reference')
            transaction_type = kwargs.get('transaction_type', 'sale')  # 'sale' or 'credit' (refund)
            
            payment_method = request.env['pos.payment.method'].browse(payment_method_id)
            if not payment_method or payment_method.use_payment_terminal != 'nmi':
                return {'error': 'Invalid payment method'}

            terminal = payment_method.pos_terminal_id
            if not terminal or not terminal.device_id or not terminal.api_key:
                return {'error': 'Terminal configuration incomplete or missing API Key/Device ID'}

            # Setup NMI transact.php payload
            url = "https://secure.networkmerchants.com/api/transact.php"
            
            # Format amount as x.xx (NMI requires string with 2 decimal places)
            formatted_amount = f"{float(amount):.2f}"
            
            payload = {
                'security_key': terminal.api_key,
                'type': transaction_type,
                'amount': formatted_amount,
                'poi_device_id': terminal.device_id,
                'response_method': 'asynchronous',
                'orderid': reference,
            }

            _logger.info("Initiating NMI cloud transaction: %s", {k: v if k != 'security_key' else '***' for k, v in payload.items()})
            
            response = requests.post(url, data=payload, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=30)
            
            if response.status_code == 200:
                # Parse query string response
                res_data = {k: v[0] for k, v in parse_qs(response.text).items()}
                _logger.info("NMI transact.php response parsed: %s", res_data)
                
                response_code = res_data.get('response_code')
                
                # 101 is 'Request Accepted' for asynchronous transactions
                if response_code == '101' and res_data.get('async_status_guid'):
                    return {
                        'status': 'inFlight',
                        'async_status_guid': res_data.get('async_status_guid'),
                    }
                else:
                    error_msg = res_data.get('responsetext', 'Unknown gateway error')
                    return {
                        'error': f"Gateway error ({response_code}): {error_msg}"
                    }
            else:
                return {'error': f"HTTP Error {response.status_code}: {response.text}"}

        except Exception as e:
            _logger.exception("NMI Payment Initiate Exception")
            return {'error': str(e)}

    @http.route('/pos/nmi/payment/poll', type='json', auth='public', methods=['POST'])
    def nmi_payment_poll(self, **kwargs):
        """Poll the status of an in-flight transaction using the AsyncStatus API."""
        try:
            payment_method_id = kwargs.get('payment_method_id')
            async_status_guid = kwargs.get('async_status_guid')

            payment_method = request.env['pos.payment.method'].browse(payment_method_id)
            if not payment_method or payment_method.use_payment_terminal != 'nmi':
                return {'error': 'Invalid payment method'}

            terminal = payment_method.pos_terminal_id
            if not terminal or not terminal.api_key:
                return {'error': 'Terminal configuration missing API Key'}

            url = f"https://secure.networkmerchants.com/api/v2/devices/asyncstatus/{async_status_guid}?responseMethod=asynchronous"
            headers = {
                "Authorization": f"Bearer {terminal.api_key}",
                "Content-Type": "application/json"
            }

            _logger.debug("Polling NMI transaction status for GUID: %s", async_status_guid)
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                res_json = response.json()
                _logger.debug("NMI Poll Response: %s", res_json)

                async_status = res_json.get('asyncStatus')
                
                if async_status in ['inFlight', 'poiDeviceInUse']:
                    return {
                        'status': 'inFlight',
                        'message': 'Waiting for cardholder interaction on device...'
                    }
                
                elif async_status == 'interactionComplete':
                    transaction = res_json.get('transaction', {})
                    success = transaction.get('success', False)
                    
                    if success:
                        # Success - Extract transaction details
                        emv_meta = transaction.get('emvMetaData', {})
                        card_type = transaction.get('card_type', '')
                        masked_pan = emv_meta.get('maskedMerchantNumber', '') or emv_meta.get('maskedPan', '')
                        
                        # Fallback for mask PAN if not present in EMV metadata
                        if not masked_pan and transaction.get('cc_number'):
                            masked_pan = transaction.get('cc_number')

                        return {
                            'status': 'Approved',
                            'transaction_id': transaction.get('id'),
                            'auth_code': transaction.get('authCode'),
                            'card_name': emv_meta.get('applicationLabel') or card_type or 'Credit Card',
                            'primary_acc_number': masked_pan,
                            'transaction_date': transaction.get('date') or fields.Datetime.now().isoformat(),
                        }
                    else:
                        error_obj = res_json.get('error', {})
                        error_msg = error_obj.get('message') or transaction.get('responsetext') or 'Transaction Declined'
                        return {
                            'status': 'Declined',
                            'error': error_msg
                        }
                
                elif async_status in ['cancelledAtTerminal', 'cancelledByTimeout', 'cancelledByApi']:
                    return {
                        'status': 'Cancelled',
                        'error': f'Transaction was cancelled ({async_status})'
                    }
                else:
                    return {
                        'status': 'Error',
                        'error': f'Unknown transaction status: {async_status}'
                    }
            else:
                try:
                    err_json = response.json()
                    err_msg = err_json.get('error', {}).get('message', response.text)
                except Exception:
                    err_msg = response.text
                return {'error': f"Polling failed (HTTP {response.status_code}): {err_msg}"}

        except Exception as e:
            _logger.exception("NMI Payment Poll Exception")
            return {'error': str(e)}

    @http.route('/pos/nmi/payment/terminate', type='json', auth='public', methods=['POST'])
    def nmi_payment_terminate(self, **kwargs):
        """Send a termination request to cancel an active in-flight transaction on the device."""
        try:
            payment_method_id = kwargs.get('payment_method_id')
            payment_method = request.env['pos.payment.method'].browse(payment_method_id)
            if not payment_method or payment_method.use_payment_terminal != 'nmi':
                return {'error': 'Invalid payment method'}

            terminal = payment_method.pos_terminal_id
            if not terminal or not terminal.device_id or not terminal.api_key:
                return {'error': 'Terminal configuration incomplete'}

            url = "https://secure.networkmerchants.com/api/transact.php"
            payload = {
                'security_key': terminal.api_key,
                'poi_device_id': terminal.device_id,
                'poi_request': 'terminate',
            }

            _logger.info("Sending termination request to NMI terminal '%s' (ID: %s)", terminal.name, terminal.device_id)
            response = requests.post(url, data=payload, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=15)
            
            if response.status_code == 200:
                res_data = {k: v[0] for k, v in parse_qs(response.text).items()}
                _logger.info("NMI Termination response: %s", res_data)
                return {'success': True, 'message': res_data.get('responsetext', 'Termination request submitted')}
            else:
                return {'error': f"HTTP {response.status_code}: {response.text}"}

        except Exception as e:
            _logger.exception("NMI Payment Terminate Exception")
            return {'error': str(e)}

    @http.route('/pos/nmi/payment/void_refund', type='json', auth='public', methods=['POST'])
    def nmi_payment_void_refund(self, **kwargs):
        """Perform a void or refund of a previously processed transaction (synchronous backend-only)."""
        try:
            payment_method_id = kwargs.get('payment_method_id')
            transaction_id = kwargs.get('transaction_id')
            amount = kwargs.get('amount')
            tx_type = kwargs.get('type', 'void')  # 'void' or 'refund'

            payment_method = request.env['pos.payment.method'].browse(payment_method_id)
            if not payment_method or payment_method.use_payment_terminal != 'nmi':
                return {'error': 'Invalid payment method'}

            terminal = payment_method.pos_terminal_id
            if not terminal or not terminal.api_key:
                return {'error': 'Terminal API Key missing'}

            url = "https://secure.networkmerchants.com/api/transact.php"
            payload = {
                'security_key': terminal.api_key,
                'type': tx_type,
                'transactionid': transaction_id,
            }
            if tx_type == 'refund' and amount:
                payload['amount'] = f"{float(amount):.2f}"

            _logger.info("Processing synchronous NMI %s for transaction %s", tx_type, transaction_id)
            response = requests.post(url, data=payload, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=30)

            if response.status_code == 200:
                res_data = {k: v[0] for k, v in parse_qs(response.text).items()}
                _logger.info("NMI %s response parsed: %s", tx_type, res_data)

                response_code = res_data.get('response_code')
                # response = '1' means Approved
                if res_data.get('response') == '1' and response_code == '100':
                    return {
                        'status': 'Approved',
                        'transaction_id': res_data.get('transactionid'),
                        'auth_code': res_data.get('authcode', ''),
                    }
                else:
                    error_msg = res_data.get('responsetext', 'Unknown error')
                    return {
                        'status': 'Declined',
                        'error': f"{tx_type.capitalize()} failed ({response_code}): {error_msg}"
                    }
            else:
                return {'error': f"HTTP {response.status_code}: {response.text}"}

        except Exception as e:
            _logger.exception("NMI Void/Refund Exception")
            return {'error': str(e)}