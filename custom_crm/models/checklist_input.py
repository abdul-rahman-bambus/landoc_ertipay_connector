import json
import logging
import requests

from odoo import fields, models, api, _
from odoo.exceptions import (
    UserError,
)


_logger = logging.getLogger(__name__)


class ChecklistInput(models.Model):
    _name = 'checklist.input'
    _description = 'Checklist Input'

    name = fields.Char(string="Checklist Name")
    lead_id = fields.Many2one(comodel_name="crm.lead", string="Lead", readonly=True)
    is_service_checklist = fields.Boolean(string="Service Checklist")
    checklist_line_ids = fields.One2many(comodel_name="checklist.input.line", inverse_name="checklist_id")
    service_checklist_line = fields.One2many(comodel_name="service.checklist.line", inverse_name="checklist_id")
    property_checklist_line = fields.One2many(comodel_name="property.checklist.line", inverse_name="checklist_id")
    state = fields.Selection(selection=[
        ('draft', "Draft"),
        ('document_verified', "Mark Documents Verified"),
        ('confirm', "Confirm"),
    ], string="Status",
        readonly=True, copy=False, index=True,
        default='draft')
    company_id = fields.Many2one(comodel_name='res.company',index=True)


    def action_set_to_confirm(self):
        """Action set to confirm"""
        # for content_checklist in self.checklist_line_ids:
        #     if content_checklist.is_data_required or content_checklist.is_attachment_required:
        #         if content_checklist.is_data_required and not content_checklist.data_field:
        #             raise UserError(_("Data is required !"))
        #         if content_checklist.is_attachment_required and not content_checklist.attachments:
        #             raise UserError(_("Attachments is required !"))

        for service_checklist in self.service_checklist_line:
            if service_checklist.is_data_required or service_checklist.is_attachment_required:
                if service_checklist.is_data_required and not service_checklist.data_field:
                    raise UserError(_(f"'{service_checklist.name}' Data is required !"))
                if service_checklist.is_attachment_required and not service_checklist.attachments:
                    raise UserError(_(f"'{service_checklist.name}' Attachments is required !"))

        for property_checklist in self.property_checklist_line:
            if property_checklist.is_data_required or property_checklist.is_attachment_required:
                if property_checklist.is_data_required and not property_checklist.data_field:
                    raise UserError(_(f"'{property_checklist.name}' Data is required !"))
                if property_checklist.is_attachment_required and not property_checklist.attachments:
                    raise UserError(_(f"'{property_checklist.name}' Attachments is required !"))
        self.state = 'confirm'

    def action_set_to_draft(self):
        """Action set to draft"""
        self.state = 'draft'


    def _send_document_correction_to_n8n(self, correction_items):
        self.ensure_one()

        lead = self.lead_id
        if not lead:
            raise UserError(_("Lead is missing for this checklist."))

        webhook_url = self.env['ir.config_parameter'].sudo().get_param(
            'landoc.n8n_document_correction_webhook_url'
        ) or 'https://n8n-demo.rizathoufique.co.in/webhook/landoc/document-correction'

        service_code = ''
        if hasattr(lead, 'service_code') and lead.service_code:
            service_code = lead.service_code
        elif hasattr(lead, 'selected_service_option') and lead.selected_service_option:
            service_code = lead.selected_service_option
        else:
            service_code = 'muslim_marriage'

        payload = {
            "event": "document_correction_required",
            "lead_id": lead.id,
            "request_number": lead.name or "",
            "service_code": service_code,

            "bot_customer_id": lead.bot_customer_id or "",
            "bot_channel": lead.bot_channel or "chat",
            "bot_session_id": lead.bot_session_id or lead.bot_customer_id or "",

            "correction_items": correction_items,
        }

        try:
            _logger.info("LANDOC: Sending document correction webhook to n8n URL: %s", webhook_url)
            _logger.info("LANDOC: Document correction payload: %s", payload)

            response = requests.post(
                webhook_url,
                json=payload,
                timeout=20
            )

            _logger.info(
                "LANDOC: n8n document correction webhook response. Status: %s Response: %s",
                response.status_code,
                response.text
            )

            # lead.message_post(
            #     body=(
            #         "Document correction webhook sent to n8n.<br/>"
            #         "<b>Status Code:</b> %s<br/>"
            #         "<b>Response:</b> %s<br/>"
            #         "<pre>%s</pre>"
            #     ) % (
            #         response.status_code,
            #         response.text,
            #         json.dumps(payload, indent=2)
            #     )
            # )

            return response.status_code in [200, 201, 202]

        except Exception as e:
            _logger.exception("LANDOC: Failed to send document correction webhook to n8n")

            lead.message_post(
                body="Failed to send document correction webhook to n8n: %s" % str(e)
            )

            return False

    def _send_documents_verified_to_n8n(self):
        self.ensure_one()

        lead = self.lead_id
        if not lead:
            raise UserError(_("Lead is missing for this checklist."))

        webhook_url = self.env['ir.config_parameter'].sudo().get_param(
            'landoc.n8n_document_verified_webhook_url'
        ) or 'https://n8n-demo.rizathoufique.co.in/webhook/landoc/document-verified'

        service_code = ''
        if hasattr(lead, 'service_code') and lead.service_code:
            service_code = lead.service_code
        elif hasattr(lead, 'selected_service_option') and lead.selected_service_option:
            service_code = lead.selected_service_option
        else:
            service_code = 'muslim_marriage'

        payload = {
            "event": "documents_verified",
            "lead_id": lead.id,
            "request_number": lead.name or "",
            "service_code": service_code,

            "bot_customer_id": lead.bot_customer_id or "",
            "bot_channel": lead.bot_channel or "chat",
            "bot_session_id": lead.bot_session_id or lead.bot_customer_id or "",

            "documents_status": "verified",
            "verified_at": fields.Datetime.now().isoformat(),
        }

        try:
            _logger.info("LANDOC: Sending document verified webhook to n8n URL: %s", webhook_url)
            _logger.info("LANDOC: Document verified payload: %s", payload)

            response = requests.post(
                webhook_url,
                json=payload,
                timeout=20
            )

            _logger.info(
                "LANDOC: n8n document verified webhook response. Status: %s Response: %s",
                response.status_code,
                response.text
            )

            # lead.message_post(
            #     body=(
            #         "Document verified webhook sent to n8n.<br/>"
            #         "<b>Status Code:</b> %s<br/>"
            #         "<b>Response:</b> %s<br/>"
            #         "<pre>%s</pre>"
            #     ) % (
            #         response.status_code,
            #         response.text,
            #         json.dumps(payload, indent=2)
            #     )
            # )

            return response.status_code in [200, 201, 202]

        except Exception as e:
            _logger.exception("LANDOC: Failed to send document verified webhook to n8n")

            lead.message_post(
                body="Failed to send document verified webhook to n8n: %s" % str(e)
            )

            return False


    def action_mark_documents_verified(self):
        for checklist in self:
            pending_lines = checklist.service_checklist_line.filtered(
                lambda line: line.bot_status != 'approved'
            )

            if pending_lines:
                raise UserError(_("All documents must be approved before marking as verified."))
            checklist.state = 'document_verified'
            checklist._send_documents_verified_to_n8n()


    