# -*- coding: utf-8 -*-
# Part of Creyox Technologies
from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        data += ['pos.terminal']
        print("Model loaded.", data)
        return data