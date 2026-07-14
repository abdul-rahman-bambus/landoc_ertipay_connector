from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    lead_id = fields.Many2one(comodel_name="crm.lead", readonly=True, tracking=1)
    transaction_no = fields.Char(string="Transaction Number")
    application_no = fields.Char(string="Application Number")
    reference_no = fields.Char(string="Reference Number")

    @api.depends('ref', 'move_type', 'partner_id', 'invoice_date', 'tax_totals')
    def _compute_duplicated_ref_ids(self):
        """
        Warning : This base function called for fixing bug (Singleton error) while onchanging any field in CRM.
                  move_to_duplicate_move = self._fetch_duplicate_reference() changed to --> move_to_duplicate_move = move._fetch_duplicate_reference()
        """
        for move in self:
            move_to_duplicate_move = move._fetch_duplicate_reference()
            # Uses move._origin.id to handle records in edition/existing records and 0 for new records
            move.duplicated_ref_ids = move_to_duplicate_move.get(move._origin, self.env['account.move'])


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    lead_id = fields.Many2one(related="move_id.lead_id")

    @api.model_create_multi
    def create(self, vals_lists):
        """Create functionality extended for adding 'analytic_distribution' """
        res = super().create(vals_lists)
        for move in res:
            if move.lead_id:
                move.analytic_distribution = {move.lead_id.analytic_account_id.id: 100.0}
        return res
