from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    ertipay_transaction_fee = fields.Monetary(
        string="Transaction Fee",
        currency_field="currency_id",
        readonly=True,
        copy=False,
    )

    ertipay_gst = fields.Monetary(
        string="GST",
        currency_field="currency_id",
        readonly=True,
        copy=False,
    )

    ertipay_total_paid = fields.Monetary(
        string="Total Paid",
        currency_field="currency_id",
        readonly=True,
        copy=False,
    )

    ertipay_session_id = fields.Char(
        string="Session ID",
        readonly=True,
        copy=False,
    )

    ertipay_payment_reference = fields.Char(
        string="Gateway Reference",
        readonly=True,
        copy=False,
    )

    payment_transaction_id = fields.Many2one(
        'payment.transaction',
        string='Payment Transaction',
        readonly=True,
        copy=False,
    )
