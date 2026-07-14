from odoo import fields, models, api

from . import closing_cash_ids as cash_closing
from . import opening_cash_ids as cash_opening

class CurrencyDenomination(models.Model):
    _name = 'currency.denomination'
    _description = 'Currency Denomination'
    _rec_name = "date"

    name = fields.Char()
    date = fields.Date(default=fields.Date.today)
    company_id = fields.Many2one(comodel_name='res.company',index=True)
    user_id = fields.Many2one(
        'res.users', string='User', default=lambda self: self.env.user,
        domain="[('share', '=', False)]",
        check_company=True, index=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, readonly=True,
                                  string="Currency ")  # currency of amount currency


    opening_cash_ids = fields.One2many(comodel_name='opening.cash.line',
                                    inverse_name='denomination_id')
    closing_cash_ids = fields.One2many(comodel_name='closing.cash.line',
                                    inverse_name='denomination_id',)

    total_opening_cash = fields.Monetary(compute="_compute_total_opening_cash")
    total_closing_cash = fields.Monetary(compute="_compute_total_closing_cash")

    @api.model
    def default_get(self, default_fields):
        defaults = super().default_get(default_fields)
        closing_list = []
        for closing in cash_closing.denomination_type:
            closing_list.append((0,0, {'cash_denomination': closing[0] }))
        opening_list = []
        for opening in cash_opening.denomination_type:
            opening_list.append((0, 0, {'cash_denomination': opening[0]}))
        defaults.update({'opening_cash_ids': opening_list, 'closing_cash_ids': closing_list})
        return defaults

    @api.depends('opening_cash_ids')
    def _compute_total_opening_cash(self):
        for record in self:
            record.total_opening_cash = sum(record.opening_cash_ids.mapped('total'))

    @api.depends('closing_cash_ids')
    def _compute_total_closing_cash(self):
        for record in self:
            record.total_closing_cash = sum(record.closing_cash_ids.mapped('total'))

