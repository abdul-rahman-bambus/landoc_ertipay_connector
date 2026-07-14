from odoo import fields, models, api


class ResSro(models.Model):
    _name = 'res.sro'
    _description = 'Res Sro'
    _rec_name = "name"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", tracking=True)
    district_id = fields.Many2one('res.district', tracking=1, string="District", required=True)
    company_id = fields.Many2one(comodel_name='res.company', tracking=1, index=True)
    zone_id = fields.Many2one(related='district_id.zone_id', tracking=1, store=True)

