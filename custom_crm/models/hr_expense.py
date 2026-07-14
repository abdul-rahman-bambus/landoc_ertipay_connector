from odoo import fields, models, api


class HrExpenses(models.Model):
    _inherit = 'hr.expense'

    lead_id = fields.Many2one(comodel_name="crm.lead", readonly=True, copy=False, tracking=1)

    @api.model_create_multi
    def create(self, vals_lists):
        """Create functionality extended for adding 'analytic_distribution' """
        res = super().create(vals_lists)
        for expense in res:
            if expense.lead_id:
                expense.analytic_distribution = {expense.lead_id.analytic_account_id.id: 100.0}
        return res
