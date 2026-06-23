# -*- coding: utf-8 -*-
# Part of Creyox Technologies
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class PosTerminal(models.Model):
    _name = 'pos.terminal'
    _inherit = ['pos.load.mixin']
    _description = 'POS Payment Terminal (NMI Cloud API)'
    _order = 'name'

    name = fields.Char(string="Terminal Name", required=True, help="A descriptive name/nickname for this terminal")

    # Cloud API Terminal Registry (Retrieved from NMI Estate Management)
    device_id = fields.Char(
        string="POI Device ID",
        required=True,
        help="The unique POI Device GUID returned by NMI"
    )
    serial_number = fields.Char(
        string="Serial Number",
        readonly=True,
        help="The hardware serial number of the registered device"
    )
    device_make = fields.Char(
        string="Device Make",
        readonly=True,
        help="The manufacturer of the device"
    )
    device_model_name = fields.Char(
        string="Device Model",
        readonly=True,
        help="The model of the device"
    )

    # Legacy/Deprecated Fields (kept for backward compatibility and database safety)
    api_key = fields.Char(string="Legacy Gateway API Key")
    environment = fields.Selection([
        ('sandbox', 'Sandbox/Test'),
        ('production', 'Production'),
    ], string="Legacy Environment")
    device_model = fields.Selection([
        ('Ingenico-iPP320-RBA', 'Ingenico iPP320 (RBA)'),
        ('Ingenico-iPP350-RBA', 'Ingenico iPP350 (RBA)'),
        ('Ingenico-iSelf-RAM', 'Ingenico iSelf (RAM)'),
    ], string="Legacy Device Model", default='Ingenico-iPP320-RBA')
    connection_type = fields.Selection([
        ('SERIAL', 'Serial (USB/COM Port)'),
        ('TCP', 'TCP/IP Network'),
    ], default='TCP', string="Legacy Connection Type")
    com_port = fields.Char(string="Legacy COM Port")
    baudrate = fields.Char(string="Legacy Baud Rate")
    ip_address = fields.Char(string="Legacy IP Address")
    tcp_port = fields.Integer(string="Legacy TCP Port", default=8000)
    server_address = fields.Char(string="Legacy Server Address", default='127.0.0.1')
    server_port = fields.Integer(string="Legacy Server Port", default=1869)
    standby_message = fields.Text(string="Legacy Standby Message")
    timeout = fields.Integer(string="Legacy Timeout", default=120)
    auto_confirm = fields.Boolean(string="Legacy Auto Confirm", default=True)
    print_receipt = fields.Boolean(string="Legacy Print Receipt", default=True)
    merchant_name = fields.Char(string="Legacy Merchant Name")
    merchant_address = fields.Text(string="Legacy Merchant Address")
    merchant_phone = fields.Char(string="Legacy Merchant Phone")

    # Status and Monitoring
    active = fields.Boolean(string="Active", default=True)
    last_test_date = fields.Datetime(string="Last Test Date", readonly=True)
    last_test_result = fields.Char(string="Last Test Result", readonly=True)
    device_status = fields.Selection([
        ('unknown', 'Unknown'),
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
        ('error', 'Error'),
    ], string="Device Status", default='unknown', readonly=True)

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Fields to load in POS frontend"""
        return [
            'name', 'device_id', 'serial_number', 'device_make', 'device_model_name',
            'active', 'device_status'
        ]

    def get_connection_config(self):
        """Get connection configuration for frontend"""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'device_id': self.device_id,
            'device_status': self.device_status,
        }