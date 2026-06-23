# -*- coding: utf-8 -*-
# Part of Creyox Technologies
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests
import logging

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    # Default POS Terminal for this Payment Method
    pos_terminal_id = fields.Many2one(
        'pos.terminal',
        string="Default POS Terminal",
        domain="[('active', '=', True)]",
        help="Select the default terminal to which Odoo POS sends payment requests"
    )

    # NMI Gateway Credentials & Environment
    nmi_api_key = fields.Char(
        string="NMI API Key",
        help="NMI Security Key for gateway authentication"
    )
    nmi_environment = fields.Selection([
        ('sandbox', 'Sandbox / Test'),
        ('production', 'Production'),
    ], default='sandbox', string="NMI Environment", required=True)

    # Wizard-like helper fields for registering a new terminal
    nmi_registration_code = fields.Char(
        string="Registration Code",
        help="Enter the 6-character rotating registration code shown on the terminal screen"
    )
    nmi_new_terminal_name = fields.Char(
        string="New Terminal Name",
        help="Give a name/nickname to identify the new terminal in Odoo"
    )

    # Other settings
    nmi_server_url = fields.Char(
        string="NMI Service URL",
        default='https://secure.networkmerchants.com/api',
        help="URL of the NMI payment service"
    )
    nmi_timeout = fields.Integer(
        string="Transaction Timeout",
        default=120,
        help="Maximum time to wait for transaction completion (seconds)"
    )
    nmi_auto_confirm = fields.Boolean(
        string="Auto Confirm",
        default=True,
        help="Automatically confirm approved transactions"
    )
    nmi_allow_partial = fields.Boolean(
        string="Allow Partial Payments",
        default=False,
        help="Allow partial payments for this payment method"
    )
    nmi_tipping_support = fields.Selection([
        ('Default', 'Use Terminal Default'),
        ('None', 'No Tipping'),
        ('OnDevice', 'On Device'),
        ('EndOfDay', 'End of Day'),
        ('Both', 'Both Methods'),
    ], default='Default', string="Tipping Support")
    nmi_print_receipt = fields.Boolean(
        string="Print Receipt",
        default=True,
        help="Print receipts for NMI transactions"
    )
    nmi_merchant_receipt = fields.Boolean(
        string="Print Merchant Copy",
        default=True,
        help="Print merchant copy of receipt"
    )
    nmi_customer_receipt = fields.Boolean(
        string="Print Customer Copy",
        default=True,
        help="Print customer copy of receipt"
    )

    def _get_payment_terminal_selection(self):
        """Add NMI terminal to the POS terminal selection"""
        return super()._get_payment_terminal_selection() + [('nmi', 'NMI Cloud API')]

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Fields to load in POS frontend"""
        fields = super()._load_pos_data_fields(config_id)
        fields += [
            'pos_terminal_id', 'nmi_api_key', 'nmi_environment', 'nmi_timeout',
            'nmi_auto_confirm', 'nmi_allow_partial', 'nmi_tipping_support',
            'nmi_print_receipt', 'nmi_merchant_receipt', 'nmi_customer_receipt'
        ]
        return fields

    @api.constrains('nmi_api_key')
    def _check_api_key_required(self):
        """Ensure NMI API key is provided if this method is configured for NMI"""
        for record in self:
            if record.use_payment_terminal == 'nmi' and not record.nmi_api_key:
                raise ValidationError(_("NMI API Key is required for NMI payment methods."))

    @api.onchange('use_payment_terminal')
    def _onchange_use_payment_terminal(self):
        """Clear NMI fields when not using NMI terminal"""
        if self.use_payment_terminal != 'nmi':
            self.pos_terminal_id = False
            self.nmi_api_key = False

    def get_nmi_config(self):
        """Get complete NMI configuration for frontend"""
        self.ensure_one()

        if self.use_payment_terminal != 'nmi':
            return {}

        config = {
            'server_url': self.nmi_server_url,
            'timeout': self.nmi_timeout,
            'auto_confirm': self.nmi_auto_confirm,
            'allow_partial': self.nmi_allow_partial,
            'tipping_support': self.nmi_tipping_support,
            'print_receipt': self.nmi_print_receipt,
            'merchant_receipt': self.nmi_merchant_receipt,
            'customer_receipt': self.nmi_customer_receipt,
            'api_key': self.nmi_api_key,
            'environment': self.nmi_environment,
        }

        if self.pos_terminal_id:
            config['terminal'] = self.pos_terminal_id.get_connection_config()

        return config

    def action_fetch_nmi_terminals(self):
        """Fetch and sync all registered terminals (POI Devices) from the NMI Account"""
        self.ensure_one()
        if not self.nmi_api_key:
            raise ValidationError(_("Please configure the NMI API Key first."))

        url = "https://secure.networkmerchants.com/api/v2/devices/list"
        headers = {
            "Authorization": f"Bearer {self.nmi_api_key}",
            "Content-Type": "application/json"
        }

        try:
            _logger.info("Fetching NMI terminals from gateway")
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                res_data = response.json()
                poi_devices = res_data.get('poiDevices', [])
                
                terminal_model = self.env['pos.terminal']
                created_count = 0
                updated_count = 0
                
                for device in poi_devices:
                    device_id = device.get('deviceId')
                    if not device_id:
                        continue
                    
                    status = device.get('connectionStatus')
                    status_mapping = {
                        'connected': 'available',
                        'disconnected': 'unavailable',
                    }
                    
                    vals = {
                        'name': device.get('deviceNickname') or f"Terminal {device.get('serialNumber') or device_id[:8]}",
                        'device_id': device_id,
                        'serial_number': device.get('serialNumber'),
                        'device_make': device.get('make'),
                        'device_model_name': device.get('model'),
                        'device_status': status_mapping.get(status, 'unknown'),
                        'last_test_date': fields.Datetime.now(),
                        'last_test_result': _("Imported from Gateway.\nConnection Status: %s") % status,
                    }
                    
                    existing = terminal_model.search([('device_id', '=', device_id)], limit=1)
                    if existing:
                        existing.write(vals)
                        updated_count += 1
                    else:
                        terminal_model.create(vals)
                        created_count += 1
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Fetch NMI Terminals"),
                        'message': _("Sync completed. Created %d and updated %d terminal records.") % (created_count, updated_count),
                        'type': 'success',
                    }
                }
            else:
                try:
                    err_data = response.json()
                    err_msg = err_data.get('error', {}).get('message', response.text)
                except Exception:
                    err_msg = response.text
                raise ValidationError(_("Failed to fetch terminals: %s") % err_msg)
        except Exception as e:
            _logger.exception("NMI Fetch Terminals exception")
            raise ValidationError(_("Failed to connect to NMI Gateway: %s") % str(e))

    def action_register_nmi_terminal(self):
        """Register a single new terminal using the rotating screen code and link it"""
        self.ensure_one()
        if not self.nmi_api_key:
            raise ValidationError(_("Please configure the NMI API Key first."))
        if not self.nmi_registration_code:
            raise ValidationError(_("Please enter the 6-character registration code shown on the device screen."))
        if not self.nmi_new_terminal_name:
            raise ValidationError(_("Please enter a name for the new terminal."))

        url = "https://secure.networkmerchants.com/api/v2/devices/register"
        headers = {
            "Authorization": f"Bearer {self.nmi_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "registrationCode": self.nmi_registration_code.strip().upper(),
            "deviceNickname": self.nmi_new_terminal_name
        }

        try:
            _logger.info("Registering NMI terminal '%s' with code '%s'", self.nmi_new_terminal_name, self.nmi_registration_code)
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                res_data = response.json()
                poi_device = res_data.get('poiDevice', {})
                
                new_terminal = self.env['pos.terminal'].create({
                    'name': poi_device.get('deviceNickname') or self.nmi_new_terminal_name,
                    'device_id': poi_device.get('poiDeviceId'),
                    'serial_number': poi_device.get('serialNumber'),
                    'device_make': poi_device.get('make'),
                    'device_model_name': poi_device.get('model'),
                    'device_status': 'available',
                    'last_test_date': fields.Datetime.now(),
                    'last_test_result': _("Device registered successfully!"),
                })
                
                self.write({
                    'pos_terminal_id': new_terminal.id,
                    'nmi_registration_code': False,
                    'nmi_new_terminal_name': False,
                })
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Register NMI Terminal"),
                        'message': _("Terminal '%s' registered successfully and set as default.") % new_terminal.name,
                        'type': 'success',
                    }
                }
            else:
                try:
                    err_data = response.json()
                    err_msg = err_data.get('error', {}).get('message', response.text)
                except Exception:
                    err_msg = response.text
                raise ValidationError(_("Registration failed: %s") % err_msg)
        except Exception as e:
            _logger.exception("NMI Registration exception")
            raise ValidationError(_("Registration failed due to connection error: %s") % str(e))

    def action_test_terminal_connection(self):
        """Test the connection status of the selected default terminal"""
        self.ensure_one()
        if not self.nmi_api_key:
            raise ValidationError(_("Please configure the NMI API Key first."))
        if not self.pos_terminal_id:
            raise ValidationError(_("No default terminal selected to test connection."))

        url = f"https://secure.networkmerchants.com/api/v2/devices/list/{self.pos_terminal_id.device_id}"
        headers = {
            "Authorization": f"Bearer {self.nmi_api_key}",
            "Content-Type": "application/json"
        }

        try:
            _logger.info("Testing connection to NMI terminal '%s' via payment method", self.pos_terminal_id.name)
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                res_data = response.json()
                poi_devices = res_data.get('poiDevices', [])
                if poi_devices:
                    device = poi_devices[0]
                    status = device.get('connectionStatus')
                    status_mapping = {
                        'connected': 'available',
                        'disconnected': 'unavailable',
                    }
                    
                    self.pos_terminal_id.write({
                        'device_status': status_mapping.get(status, 'unknown'),
                        'serial_number': device.get('serialNumber'),
                        'device_make': device.get('make'),
                        'device_model_name': device.get('model'),
                        'last_test_date': fields.Datetime.now(),
                        'last_test_result': _("Tested from Payment Method.\nConnection Status: %s") % status,
                    })
                    msg = _("Terminal '%s' connection status is %s.") % (self.pos_terminal_id.name, status)
                    msg_type = 'success' if status == 'connected' else 'warning'
                else:
                    msg = _("Terminal not found on NMI Gateway.")
                    msg_type = 'danger'
            else:
                try:
                    err_data = response.json()
                    err_msg = err_data.get('error', {}).get('message', response.text)
                except Exception:
                    err_msg = response.text
                msg = _("Test connection failed: %s") % err_msg
                msg_type = 'danger'
        except Exception as e:
            msg = _("Connection error: %s") % str(e)
            msg_type = 'danger'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Terminal Connection Test"),
                'message': msg,
                'type': msg_type,
            }
        }