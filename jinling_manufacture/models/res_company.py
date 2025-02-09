from odoo import fields,api,models




class ResCompany(models.Model):
    _inherit = 'res.company'


    def _get_html_table(self,vl):
        # vl = {'col':[],'val':[[]]}
        res = "<table style='width:100%;'><tr>"
        for th in vl['col']:
            res+="<th>%s</th>" % th
        res+="</tr>"
        for line in vl['val']:
            res+="<tr>"
            for v in line:
                res+="<td>%s</td>" % v
            res+="</tr>"
        res+="</table>"
        return res