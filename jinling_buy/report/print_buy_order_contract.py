# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/2/12
Description: print_buy_order_contract
"""


from odoo import api,fields,models


class PrintBuyOrderContract(models.AbstractModel):
    _name = 'jinling_buy.print.contract'


    def _get_report_values(self,docids,data=None):

        report_obj = self.env['ir.actions.report']
        report = report_obj._get_report_from_name('jinling_buy.report_buy_order_template')
        docargs = {
            'doc_ids':docids,
            'doc_model':report.model,
            'docs':self
        }
        return docargs