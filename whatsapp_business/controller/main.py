# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import json
import logging
from markupsafe import Markup
from werkzeug.exceptions import Forbidden
from http import HTTPStatus

from odoo import http, _
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class WhatsAppWebhookController(http.Controller):

    @http.route('/whatsapp/webhook/', methods=['POST'], type="json", auth="public")
    def handle_whatsapp_webhook_post(self):
        """Handle incoming WhatsApp webhook POST requests."""
        _logger.debug("Received WhatsApp webhook POST request.")
        try:
            payload = json.loads(request.httprequest.data)
        except Exception as e:
            _logger.error("Failed to parse webhook payload: %s", e)
            raise Forbidden()

        for entry in payload.get('entry', []):
            whatsapp_app_id = entry.get('id')
            account_record = self._get_account_record(whatsapp_app_id)
            if not self._is_signature_valid(account_record):
                _logger.warning("Signature validation failed for app_id: %s", whatsapp_app_id)
                raise Forbidden()

            for change in entry.get('changes', []):
                self._process_change(change, whatsapp_app_id)

    def _get_account_record(self, whatsapp_app_id):
        """Retrieve the WhatsApp account record by app ID."""
        return request.env['whatsapp.account.details'].sudo().search([
            ('whatsapp_app_id', '=', whatsapp_app_id)
        ])

    def _process_change(self, change, whatsapp_app_id):
        """Process a single change entry from the webhook."""
        change_data = change.get('value', {})
        phone_number_id = (
            change_data.get('metadata', {}).get('phone_number_id') or
            change_data.get('whatsapp_business_api_data', {}).get('phone_number_id')
        )

        if phone_number_id:
            self._handle_phone_number_change(change, change_data, phone_number_id, whatsapp_app_id)

        template_uid = change_data.get('message_template_id')
        if template_uid:
            self._handle_template_change(change, change_data, template_uid)

    def _handle_phone_number_change(self, change, change_data, phone_number_id, whatsapp_app_id):
        """Handle changes related to phone numbers."""
        whatsapp_account = request.env['whatsapp.account.details'].sudo().search([
            ('phone_number_id', '=', phone_number_id),
            ('whatsapp_app_id', '=', whatsapp_app_id),
        ])
        if not whatsapp_account:
            _logger.warning("No configured WhatsApp account found for webhook: %s", change_data)
            return

        if change.get('field') == 'messages':
            request.env['whatsapp.message.info']._process_statuses(change_data)
            whatsapp_account._process_messages(change_data)

    def _handle_template_change(self, change, change_data, template_uid):
        """Handle changes related to message templates."""
        template_obj = request.env['template.whatsapp'].sudo().with_context(active_test=False).search([
            ('meta_template_id', '=', template_uid)
        ])
        if not template_obj:
            _logger.warning("Template not found for UID: %s", template_uid)
            return

        field_name = change.get('field')
        if field_name == 'message_template_status_update':
            self._update_template_status(template_obj, change_data)
        elif field_name == 'template_category_update':
            template_obj.write({'category_type': change_data.get('new_category', '').lower()})
        else:
            _logger.warning("Unhandled template webhook field: %s", field_name)

    def _update_template_status(self, template_obj, change_data):
        """Update the status of a WhatsApp message template."""
        new_state = change_data.get('event', '').lower()
        template_obj.write({'state': new_state})
        if new_state == 'rejected':
            rejection_reason = (
                change_data.get('other_info', {}).get('description') or
                change_data.get('reason')
            )
            body = _("Your Template has been rejected.")
            if rejection_reason:
                body += Markup("<br/>") + _("Reason : %s", rejection_reason)
            template_obj.message_post(body=body)

    @http.route('/whatsapp/webhook/', methods=['GET'], type="http", auth="public", csrf=False)
    def verify_whatsapp_webhook(self, **params):
        """Verify WhatsApp webhook endpoint for GET requests."""
        _logger.debug("Received WhatsApp webhook verification GET request.")
        token = params.get('hub.verify_token')
        mode = params.get('hub.mode')
        challenge = params.get('hub.challenge')

        if not all([token, mode, challenge]):
            _logger.warning("Missing verification parameters: %s", params)
            return Forbidden()

        wa_account = request.env['whatsapp.account.details'].sudo().search([
            ('webhook_token', '=', token)
            # ('hardcoded_token', '=', token) # Used for Ngrock token.
        ])
        if mode == 'subscribe' and wa_account:
            response = request.make_response(challenge)
            response.status_code = HTTPStatus.OK
            return response

        response = request.make_response({})
        response.status_code = HTTPStatus.FORBIDDEN
        return response

    def _is_signature_valid(self, account_record):
        """Validate the X-Hub-Signature-256 header using the app secret."""
        signature = request.httprequest.headers.get('X-Hub-Signature-256')
        if not signature or not signature.startswith('sha256=') or len(signature) != 71:
            _logger.warning('Invalid signature header: %r', signature)
            return False

        if not account_record or not account_record.app_secret:
            _logger.warning('Missing app secret; cannot validate signature')
            return False

        expected_signature = hmac.new(
            account_record.app_secret.encode(),
            msg=request.httprequest.data,
            digestmod=hashlib.sha256,
        ).hexdigest()

        is_valid = consteq(signature[7:], expected_signature)
        if not is_valid:
            _logger.warning('Signature mismatch: expected %s, got %s', expected_signature, signature[7:])
        return is_valid
