# -*- coding: utf-8 -*-
# Part of Creyox Technologies
from odoo import models, fields, api

class PosPayment(models.Model):
    _inherit = 'pos.payment'

    nmi_reference = fields.Char(string="NMI Transaction Reference")
    transaction_auth_code = fields.Char(string="Authorization Code")
    retrieval_ref_no = fields.Char(string="Retrieval Reference Number")
    primary_acc_number = fields.Char(string="Primary Account Number")
    transaction_date = fields.Char(string="Transaction Date")
    card_name = fields.Char(string="Card Name")
    last_four_digits = fields.Char(string="Last Four Digits")

class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _payment_fields(self, order, ui_paymentline):
        payment_fields = super()._payment_fields(order, ui_paymentline)
        payment_fields.update({
            'nmi_reference': ui_paymentline.get('nmi_reference'),
            'transaction_auth_code': ui_paymentline.get('transaction_auth_code'),
            'retrieval_ref_no': ui_paymentline.get('retrieval_ref_no'),
            'primary_acc_number': ui_paymentline.get('primary_acc_number'),
            'transaction_date': ui_paymentline.get('transaction_date'),
            'card_name': ui_paymentline.get('card_name'),
            'last_four_digits': ui_paymentline.get('primary_acc_number')[-4:] if ui_paymentline.get('primary_acc_number') else '',
        })
        return payment_fields