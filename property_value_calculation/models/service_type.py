from odoo import fields, models, api


class ServiceType(models.Model):
    _inherit = 'service.type'

    stamp_duty = fields.Float(default=0)
    is_stamp_percentage = fields.Boolean(default=False)
    registration_fee = fields.Float(default=0)
    is_registration_fee = fields.Boolean(default=False)
    is_registration_fee_percentage = fields.Boolean(default=False)

