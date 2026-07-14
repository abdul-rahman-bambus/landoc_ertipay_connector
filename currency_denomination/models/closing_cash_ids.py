from odoo import fields, models, api

denomination_type =[
    ('1', "₹ 1.00"),
    ('2', "₹ 2.00"),
    ('5', "₹ 5.00"),
    ('10', "₹ 10.00"),
    ('20', "₹ 20.00"),
    ('50', "₹ 50.00"),
    ('100', "₹ 100.00"),
    ('200', "₹ 200.00"),
    ('500', "₹ 500.00"),
    ]

class ClosingCashIds(models.Model):
    _name = 'closing.cash.line'
    _description = 'Closing Cash Line'

    name = fields.Char()
    denomination_id = fields.Many2one(comodel_name='currency.denomination')
    cash_denomination = fields.Selection(selection=denomination_type, readonly=True, string="Cash Denomination", copy=False, index=True)
    count = fields.Integer(string="Count")
    currency_id = fields.Many2one('res.currency', default=lambda self:self.env.company.currency_id, readonly=True,
                                  string="Currency .")  # currency of amount currency
    company_id = fields.Many2one(comodel_name='res.company',index=True)
    total = fields.Monetary(string="Total", compute="_compute_total")

    @api.depends('cash_denomination', 'count')
    def _compute_total(self):
        for record in self:
            record.total = int(record.cash_denomination) * record.count
