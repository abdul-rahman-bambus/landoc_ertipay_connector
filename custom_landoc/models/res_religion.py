from odoo import models, fields, api

class Religion(models.Model):
    _name = "res.religion"
    _description = "Religion Information"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Religion Name", tracking=1, required=True)
    code = fields.Char(string="Code", compute="_compute_code")
    company_id = fields.Many2one(comodel_name='res.company', tracking=1, index=True)

    @api.depends('name')
    def _compute_code(self):
        for religion in self:
            religion_code = religion.name.replace(" ", "_") if religion.name else religion.name
            religion.code = religion_code.lower() if religion_code else False

