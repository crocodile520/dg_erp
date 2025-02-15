# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/2/13
Description: print_sell_out
"""


from odoo import api,fields,models


class PrintsellOut(models.AbstractModel):
    _name = 'jinling_sell.print.out'


    def _get_report_values(self,docids,data=None):

        report_obj = self.env['ir.actions.report']
        report = report_obj._get_report_from_name('jinling_sell.report_sell_out_template')
        docargs = {
            'doc_ids':docids,
            'doc_model':report.model,
            'docs':self
        }
        return docargs