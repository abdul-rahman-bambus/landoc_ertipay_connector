from odoo import fields, models, api

class PWDFloorLine(models.Model):
    _inherit = 'pwd.floor.line'
    _description = 'PWD Floor Line'

    landoc_service_id = fields.Many2one('crm.landoc.service')
