
from odoo import models, fields

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    def action_validate_expenses(self):
        """
         Automate validation of expenses.
         If payment_mode: company_account validate and create expense sheet and create journal.
         If payment_mode: own_account validate and create expense sheet and create journal and initiate payment.
        """
        sheets = self._create_sheets_from_expense()
        sheets.action_submit_sheet()
        sheets.action_approve_expense_sheets()
        sheets.action_sheet_move_post()
        if self.payment_mode == 'own_account':
            return {
                'name': 'Register Vendor Payment',
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment.register',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'active_model': 'account.move',
                    'active_ids': sheets.account_move_ids.ids,
                },
            }
