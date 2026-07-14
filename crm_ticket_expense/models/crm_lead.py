from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    sale_order_ids = fields.One2many(
        'sale.order',
        'opportunity_id',
        string='Sale Orders'
    )

    expense_ids = fields.One2many(
        'hr.expense',
        'lead_id',
        string='Expenses'
    )

    # invoice_ids
    payment_move_ids = fields.One2many(
        'account.move',
        'lead_id',
        string='Payments ',
        domain=[('move_type', 'in', ('out_receipt', 'out_invoice'))],
        readonly=True
    )

    # vendor_bill_ids
    vendor_payment_move_ids = fields.One2many(
        'account.move',
        'lead_id',
        string='Payments',
        domain=[('move_type', 'in', ('in_receipt', 'in_invoice'))],
        readonly=True
    )

    expense_count = fields.Integer(compute="_compute_expense_count")
    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
        string="Currency "
    )
    invoice_amount_due = fields.Monetary(compute="_compute_invoice_due", currency_field='company_currency_id')

    # ##################
    # FINANCIAL TOTALS
    # ##################
    ticket_invoiced_amount = fields.Monetary(
        compute='_compute_ticket_financials',
        currency_field='company_currency_id',
        string='Invoiced Revenue'
    )

    ticket_collected_amount = fields.Monetary(
        compute='_compute_ticket_financials',
        currency_field='company_currency_id',
        string='Collected Amount'
    )

    ticket_expense_amount = fields.Monetary(
        compute='_compute_ticket_financials',
        currency_field='company_currency_id',
        string='Expenses '
    )

    ticket_outstanding_amount = fields.Monetary(
        compute='_compute_ticket_financials',
        currency_field='company_currency_id',
        string='Outstanding'
    )

    ticket_accounting_margin = fields.Monetary(
        compute='_compute_ticket_financials',
        currency_field='company_currency_id',
        string='Accounting Margin'
    )

    ticket_cash_margin = fields.Monetary(
        compute='_compute_ticket_financials',
        currency_field='company_currency_id',
        string='Cash Margin'
    )

    ticket_collection_ratio = fields.Float(
        compute='_compute_ticket_collection_ratio',
        string='Collection %'
    )

    ticket_financial_status = fields.Selection(
        [
            ('profit', 'Profit'),
            ('loss', 'Loss'),
            ('pending', 'Pending Collection'),
            ('not_started', 'No Financial Activity')
        ],
        compute='_compute_ticket_financial_status',
        string='Financial Status'
    )

    # ###################
    # VISIBILITY
    # ###################

    can_confirm_quotation = fields.Boolean(
        compute='_compute_button_visibility'
    )

    can_create_invoice = fields.Boolean(
        compute='_compute_button_visibility'
    )

    can_register_payment = fields.Boolean(
        compute='_compute_button_visibility'
    )

    can_register_vendor_payment = fields.Boolean(
        compute='_compute_button_visibility'
    )

    can_show_vendor = fields.Boolean(compute='_compute_button_visibility')

    # ####################
    # COMPUTE FINANCIALS
    # ####################

    @api.depends(
        'ticket_invoiced_amount',
        'ticket_collected_amount',
        'ticket_expense_amount',
        'ticket_outstanding_amount',
        'ticket_accounting_margin',
        'payment_move_ids',
        'vendor_payment_move_ids',
        'invoice_ids',
        'expense_ids'
    )
    def _compute_ticket_financial_status(self):
        for lead in self:
            if not lead.ticket_invoiced_amount and not lead.ticket_collected_amount:
                lead.ticket_financial_status = 'not_started'
            elif lead.ticket_outstanding_amount > 0:
                lead.ticket_financial_status = 'pending'
            elif lead.ticket_accounting_margin < 0:
                lead.ticket_financial_status = 'loss'
            else:
                lead.ticket_financial_status = 'profit'

    @api.depends('payment_move_ids', 'vendor_payment_move_ids', 'invoice_ids', 'expense_ids')
    def _compute_ticket_collection_ratio(self):
        for lead in self:
            if lead.ticket_invoiced_amount:
                lead.ticket_collection_ratio = (lead.ticket_collected_amount / lead.ticket_invoiced_amount) * 100
            else:
                lead.ticket_collection_ratio = 0.0

    @api.depends('payment_move_ids', 'vendor_payment_move_ids', 'invoice_ids', 'expense_ids')
    def _compute_ticket_financials(self):
        AccountMove = self.env['account.move']
        HrExpense = self.env['hr.expense']

        for lead in self:
            # -----------------------------
            # Invoiced Revenue
            # -----------------------------
            invoices = AccountMove.search([
                ('lead_id', '=', lead.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
            ])
            invoiced_amount = sum(invoices.mapped('amount_total'))

            # -----------------------------
            # Collected Amount (Payments)
            # -----------------------------
            # Customer Invoice
            payments = AccountMove.search([
                ('lead_id', '=', lead.id),
                ('move_type', 'in', ('out_receipt', 'out_invoice')),
                ('state', '=', 'posted'),
            ])
            # Vendor Bills
            vendor_payments = AccountMove.search([
                ('lead_id', '=', lead.id),
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
            ])
            collected_amount = sum(payments.mapped('amount_total')) - sum(payments.mapped('amount_residual'))

            # -----------------------------
            # Expenses
            # -----------------------------
            expenses = HrExpense.search([
                ('lead_id', '=', lead.id),
                ('state', 'in', ('approved', 'done')),
            ])
            vendor_amount_total = sum(vendor_payments.mapped('amount_total')) - sum(
                vendor_payments.mapped('amount_residual'))
            expense_amount = sum(expenses.mapped('total_amount') + [vendor_amount_total])

            # -----------------------------
            # Derived Values
            # -----------------------------
            lead.ticket_invoiced_amount = invoiced_amount
            lead.ticket_collected_amount = collected_amount
            lead.ticket_expense_amount = expense_amount
            lead.ticket_outstanding_amount = invoiced_amount - collected_amount
            lead.ticket_accounting_margin = invoiced_amount - expense_amount
            lead.ticket_cash_margin = collected_amount - expense_amount

    @api.depends('payment_move_ids', 'vendor_payment_move_ids', 'invoice_ids')
    def _compute_invoice_due(self):
        for lead in self:
            invoices = self.env['account.move'].search([
                ('lead_id', '=', lead.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
            ])
            lead.invoice_amount_due = sum(invoices.mapped('amount_residual'))

    @api.depends('expense_ids')
    def _compute_expense_count(self):
        for lead in self:
            lead.expense_count = self.env['hr.expense'].search_count([
                ('lead_id', '=', lead.id)
            ])

    # ###########################
    # COMPUTE BUTTON VISIBILITY
    # ###########################

    @api.depends('sale_order_ids', 'payment_move_ids', 'vendor_payment_move_ids', 'ticket_outstanding_amount',
                 'service_id', 'expense_ids')
    def _compute_button_visibility(self):
        for lead in self:
            lead.can_confirm_quotation = any(
                order.state == 'draft' for order in lead.sale_order_ids
            )

            lead.can_create_invoice = any(
                order.invoice_status != 'invoiced'
                for order in lead.sale_order_ids
            )

            lead.can_register_payment = lead.ticket_outstanding_amount > 0

            lead.can_register_vendor_payment = any(
                bill.state == 'posted' and bill.amount_residual > 0
                for bill in lead.vendor_payment_move_ids
            )

            lead.can_show_vendor = any(self.env['landoc.fees'].search(
                [('service_id', '=', lead.service_id.id), ('is_govt_online_payment_required', '=', True)], limit=1))

    # #########################
    # ACTIONS
    # #########################

    def action_confirm_quotation(self):
        self.ensure_one()
        draft_orders = self.sale_order_ids.filtered(
            lambda o: o.state == 'draft'
        )
        if not draft_orders:
            raise UserError("No draft quotations found.")
        draft_orders.action_confirm()

    def action_create_invoice(self):
        self.ensure_one()
        orders = self.sale_order_ids.filtered(
            lambda o: o.state == 'sale'
        )
        if not orders:
            raise UserError("No confirmed Sale Orders found.")
        invoices = orders._create_invoices()
        invoices.write({'lead_id': self.id})
        invoices.action_post()

    def action_register_payment(self):
        self.ensure_one()
        invoices = self.payment_move_ids.filtered(
            lambda inv: inv.state == 'posted' and inv.amount_residual > 0
        )
        if not invoices:
            raise UserError("No outstanding invoices found.")

        return {
            'name': 'Register Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'account.move',
                'active_ids': invoices.ids,
            },
        }

    def action_create_vendor_bills(self):
        move_lines = []
        landoc_fees_obj = self.env['landoc.fees'].search([('service_id', '=', self.service_id.id)])
        if landoc_fees_obj.is_govt_online_payment_required:
            for vendor_line in landoc_fees_obj.vendor_fees_line:
                move_lines.append((0, 0, {'product_id': vendor_line.product_id.id,
                                          'quantity': 1,
                                          'tax_ids': vendor_line.tax_ids.ids,
                                          'price_unit': self.ec_additional_year_amount if vendor_line.ec_vendor_fee_category == 'search_fee_additional_year' else vendor_line.rate,
                                          'analytic_distribution': {self.analytic_account_id.id: 100}}))
        params = self.env['ir.config_parameter'].sudo()
        landoc_vendor_id = int(params.get_param('custom_landoc.landoc_vendor_id')) or False
        if not landoc_vendor_id:
            raise UserError(_("There is no default landoc vendor."))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bills',
            'res_model': 'account.move',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_lead_id': self.id, 'default_move_type': 'in_invoice',
                        'default_invoice_date': date.today(), 'default_partner_id': landoc_vendor_id,
                        'default_invoice_line_ids': move_lines}
        }

    def action_register_vendor_payment(self):
        self.ensure_one()

        vendor_bills = self.vendor_payment_move_ids.filtered(
            lambda bill: bill.state == 'posted' and bill.amount_residual > 0
        )

        if not vendor_bills:
            raise UserError("No outstanding vendor bills found.")

        return {
            'name': 'Register Vendor Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'account.move',
                'active_ids': vendor_bills.ids,
            },
        }

    def action_log_expense(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Log Expense',
            'res_model': 'hr.expense',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_lead_id': self.id,
                'default_payment_mode': 'company_account',
                'default_analytic_distribution': {self.analytic_account_id.id: 100.0}
            }
        }
