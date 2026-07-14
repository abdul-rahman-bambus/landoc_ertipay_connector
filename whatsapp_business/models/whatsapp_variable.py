from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError


class WhatsappVariables(models.Model):
    _name = 'whatsapp.variable'
    _description = 'Whatsapp Variables'
    _order = 'sequence'

    name = fields.Char(string="Variable", store=True)
    template_id = fields.Many2one('template.whatsapp')
    temp_value = fields.Char(string="Temporary Value")
    variable_field = fields.Char(string="Variable Field")
    sequence = fields.Integer(string="Sequence")
    model = fields.Char(
        string='Related Document Model',
        related='template_id.model',
        precompute=True, store=True, readonly=True)

