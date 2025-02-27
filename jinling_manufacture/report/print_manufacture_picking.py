# -*- coding: utf-8 -*-
"""
Author: Tuna
Date: 2025/2/27
Description: print_manufacture_picking
"""

from odoo import api,fields,models


class PrintManufacturePicking(models.AbstractModel):
    _name = 'jinling_manufacture.print.picking'


    def _get_report_values(self,docids,data=None):

        report_obj = self.env['ir.actions.report']
        report = report_obj._get_report_from_name('jinling_manufacture.report_manufacture_picking_template')
        docargs = {
            'doc_ids':docids,
            'doc_model':report.model,
            'docs':self
        }
        return docargs