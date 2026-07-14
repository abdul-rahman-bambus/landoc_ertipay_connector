import json
import logging
import requests

from odoo import fields, models, api, _
from odoo.exceptions import (
    UserError, ValidationError
)

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    bot_customer_id = fields.Char(string='Bot Customer ID')
    bot_channel = fields.Char(string='Bot Channel')
    bot_session_id = fields.Char(string='Bot Session ID')
    bot_current_stage = fields.Char(string='Bot Current Stage')
    bot_active_service = fields.Char(string='Bot Active Service')
    bot_workflow_source = fields.Char(string='Bot Workflow Source')
    bot_callback_reference  = fields.Char(string='Bot Callback Reference')


    def _send_payment_status_to_n8n(
        self,
        payment_status='paid',
        paid_amount=0.0,
        total_amount=0.0,
        payment_reference='',
        quotation=None,
        invoice=None,
        transaction=None,
    ):
        self.ensure_one()

        webhook_url = 'https://n8n-demo.rizathoufique.co.in/webhook/landoc/payment-status'

        payload = {
            "event": "payment_confirmed",

            "lead_id": self.id,
            "request_number": self.name,

            "quotation_id": quotation.id if quotation else '',
            "quotation_number": quotation.name if quotation else '',

            "invoice_id": invoice.id if invoice else '',
            "invoice_number": invoice.name if invoice else '',

            "transaction_id": transaction.id if transaction else '',
            "transaction_reference": transaction.reference if transaction else '',

            "payment_status": payment_status,
            "paid_amount": paid_amount,
            "total_amount": total_amount,
            "payment_reference": payment_reference,

            "bot_customer_id": self.bot_customer_id or '',
            "bot_channel": self.bot_channel or 'chat',
            "bot_session_id": self.bot_session_id or self.bot_customer_id or '',
        }

        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=20
            )

            _logger.info(
                "n8n payment webhook sent. Status: %s Response: %s",
                response.status_code,
                response.text
            )

            # self.message_post(
            #     body="Payment status webhook sent to n8n.<br/><pre>%s</pre>" %
            #     json.dumps(payload, indent=2)
            # )

            return True

        except Exception as e:
            _logger.exception("Failed to send payment status webhook to n8n")

            self.message_post(
                body="Failed to send payment status webhook to n8n: %s" % str(e)
            )

            return False
