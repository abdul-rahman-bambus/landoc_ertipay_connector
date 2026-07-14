from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        res.update({'lead_id': self.opportunity_id.id})
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    lead_id = fields.Many2one(related="order_id.opportunity_id")
    landoc_fee_line_id = fields.Many2one('landoc.customer.fees')


    @api.depends('product_id', 'company_id', 'landoc_fee_line_id.tax_ids')
    def _compute_tax_id(self):
        super()._compute_tax_id()
        for line in self:
            if line.landoc_fee_line_id:
                line.tax_id = line.landoc_fee_line_id.tax_ids

    @api.model_create_multi
    def create(self, vals_lists):
        """Create functionality extended for adding 'analytic_distribution' """
        res = super().create(vals_lists)
        for line in res:
            if line.lead_id:
                line.analytic_distribution = {line.lead_id.analytic_account_id.id: 100.0}
        return res
