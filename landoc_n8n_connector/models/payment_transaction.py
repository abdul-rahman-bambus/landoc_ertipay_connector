import logging

from odoo import models

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def write(self, vals):
        previous_states = {tx.id: tx.state for tx in self}

        result = super().write(vals)

        for tx in self:
            old_state = previous_states.get(tx.id)
            new_state = tx.state

            # Trigger only when transaction becomes paid/done
            if old_state != new_state and new_state == 'done':
                tx._landoc_notify_payment_done_to_bot()

        return result

    def _landoc_notify_payment_done_to_bot(self):
        for tx in self:
            try:
                sale_order = tx.sale_order_ids[:1] if hasattr(tx, 'sale_order_ids') else False

                if not sale_order:
                    _logger.info("No sale order found for transaction %s", tx.reference)
                    continue

                lead = sale_order.opportunity_id if hasattr(sale_order, 'opportunity_id') else False

                if not lead:
                    _logger.info("No lead/opportunity found for sale order %s", sale_order.name)
                    continue

                total_amount = sale_order.amount_total or tx.amount or 0.0
                paid_amount = tx.amount or 0.0

                payment_status = 'paid'
                if paid_amount >= total_amount:
                    payment_status = 'paid'
                elif paid_amount > 0:
                    payment_status = 'partial_paid'
                else:
                    payment_status = 'pending'

                invoice = sale_order.invoice_ids[:1] if sale_order.invoice_ids else False

                lead._send_payment_status_to_n8n(
                    payment_status=payment_status,
                    paid_amount=paid_amount,
                    total_amount=total_amount,
                    payment_reference=tx.reference or '',
                    quotation=sale_order,
                    invoice=invoice,
                    transaction=tx,
                )

            except Exception:
                _logger.exception("Error while notifying n8n for transaction %s", tx.reference)