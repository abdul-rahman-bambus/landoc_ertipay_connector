from odoo import fields, models, api


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    lead_id = fields.Many2one(comodel_name="crm.lead", readonly=True, tracking=True)

    name = fields.Char(
        string='Analytic Account',
        index='trigram',
        required=True,
        readonly=True,
        tracking=True,
        translate=True,
    )
