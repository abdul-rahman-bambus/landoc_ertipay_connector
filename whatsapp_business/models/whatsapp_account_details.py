from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import secrets
import string
import logging
import mimetypes
from odoo.tools import plaintext2html

_logger = logging.getLogger(__name__)


class AccountDetails(models.Model):
    _name = 'whatsapp.account.details'
    _description = 'Whatsapp Account Details'

    # ----------------------------------------
    # Fields
    # ----------------------------------------
    name = fields.Char(string='Account Name', required=True)
    account_app_id = fields.Char(string='App ID', required=True)
    whatsapp_app_id = fields.Char(string='WhatsApp Business App ID', required=True)
    access_token = fields.Char(string='Access Token', required=True, groups='whatsapp_business.group_whatsapp_business_manager')
    phone_number_id = fields.Char(string='Phone Number ID', required=True)
    app_secret = fields.Char(string='App Secret', required=True, groups='whatsapp_business.group_whatsapp_business_manager')
    recipient_waid = fields.Char(string='Recipient WAID')
    version = fields.Char(string='API Version', default='v13.0')
    is_active = fields.Boolean(string='Is Active', default=True)
    notify_users_ids = fields.Many2many('res.users')
    # webhook
    is_ngrok = fields.Boolean(string="Using Ngrok")
    ngrok_url = fields.Char(string="Ngrok URL")
    webhook_url = fields.Char(string="Webhook URL", compute="_compute_webhook_url", readonly=True, copy=False)
    hardcoded_token = fields.Char(string="Ngrok Token")
    webhook_token = fields.Char(string="Webhook Token", compute="_compute_generate_token", groups='whatsapp_business.group_whatsapp_business_manager', store=True)

    # ----------------------------------------
    # Compute Methods
    # ----------------------------------------

    def _compute_webhook_url(self):
        """Compute the webhook URL based on whether Ngrok is used."""
        for account in self:
            if account.is_ngrok:
                account.webhook_url = f"{account.ngrok_url}/whatsapp/webhook"
            else:
                account.webhook_url = f"{self.get_base_url()}/whatsapp_business/webhook"

    @api.depends('account_app_id')
    def _compute_generate_token(self):
        """Generate a random webhook verification token if not already set."""
        for rec in self:
            if rec.id and not rec.webhook_token:
                rec.webhook_token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))

    # ----------------------------------------
    # Helper Methods
    # ----------------------------------------

    def action_test_connection(self):
        """
        Test the connection to the WhatsApp Business API.
        Raises UserError if credentials are missing or invalid.
        """
        if not self.access_token or not self.whatsapp_app_id:
            raise UserError(_("Access Token and WhatsApp Business App ID must be set to test the connection."))
        try:
            return self._test_meta_whatsapp_credentials(
                self.account_app_id, self.app_secret, self.whatsapp_app_id, self.phone_number_id
            )
        except requests.exceptions.RequestException as e:
            raise UserError(_("Connection error: %s") % str(e))

    def get_app_token(self, app_id, app_secret):
        """
        Get app access token to test App ID + App Secret.
        Raises UserError if credentials are invalid.
        """
        url = "https://graph.facebook.com/oauth/access_token"
        params = {
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "client_credentials"
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json().get("access_token")
        raise UserError(_("Invalid App ID or Secret: %s") % response.text)

    def verify_business_account(self, business_id, access_token):
        """
        Verify if Business Account ID is valid.
        Raises UserError if invalid.
        """
        response = self.env['whatsapp.api.services'].get_request(
            f"{business_id}",
            params={"access_token": access_token},
            response_only=True
        )
        if response.status_code == 200:
            return True
        raise UserError(_("Invalid Business Account ID: %s") % response.text)

    def verify_phone_number(self, phone_number_id, access_token):
        """
        Verify if Phone Number ID is valid.
        Raises UserError if invalid.
        """
        response = self.env['whatsapp.api.services'].get_request(
            f"{phone_number_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            response_only=True
        )
        if response.status_code == 200:
            return True
        raise UserError(_("Invalid Phone Number ID: %s") % response.text)

    def _test_meta_whatsapp_credentials(self, app_id, app_secret, business_id, phone_number_id):
        """
        Test all WhatsApp credentials and return a success notification.
        Raises UserError if any step fails.
        """
        self.get_app_token(app_id, app_secret)
        self.verify_business_account(business_id, self.access_token)
        self.verify_phone_number(phone_number_id, self.access_token)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("Test connection successful!"),
            }
        }

    def _find_active_channel(self, sender_mobile_formatted, sender_name=False, create_if_not_found=False):
        """
        Find or create the active channel for the given sender mobile number.
        """
        self.ensure_one()
        whatsapp_message = self.env['whatsapp.message.info'].sudo().search(
            [
                ('formated_mobile_number', '=', sender_mobile_formatted),
                ('account_id', '=', self.id),
                ('template_id', '!=', False),
                ('state', 'not in', ['outgoing', 'error', 'cancel']),
            ], limit=1, order='id desc')
        return self.env['discuss.channel'].sudo().create_whatsapp_channel(
            whatsapp_number=sender_mobile_formatted,
            wa_account_id=self,
            sender_name=sender_name,
            create_if_not_found=create_if_not_found,
        )

    def _process_messages(self, value):
        """
        Process messages received via webhook.
        Handles:
         - Text Message
         - Attachment Message with caption
         - Location Message
         - Contact Message
         - Message Reactions
        """
        # Normalize input if necessary
        if 'messages' not in value and value.get('whatsapp_business_api_data', {}).get('messages'):
            value = value['whatsapp_business_api_data']

        for message in value.get('messages', []):
            parent_msg_id = None
            parent_id = None
            channel = None
            sender_name = value.get('contacts', [{}])[0].get('profile', {}).get('name')
            sender_mobile = message['from']
            message_type = message['type']

            # Handle parent message context
            if 'context' in message and message['context'].get('id'):
                parent_whatsapp_message = self.env['whatsapp.message.info'].sudo().search(
                    [('message_id', '=', message['context']['id'])])
                if parent_whatsapp_message:
                    parent_msg_id = parent_whatsapp_message.id
                    parent_id = parent_whatsapp_message.mail_message_id
                if parent_id:
                    channel = self.env['discuss.channel'].sudo().search([('message_ids', 'in', parent_id.id)], limit=1)

            if not channel:
                channel = self._find_active_channel(sender_mobile, sender_name=sender_name, create_if_not_found=True)

            kwargs = {
                'message_type': 'whatsapp_message',
                'author_id': channel.whatsapp_partner_id.id,
                'parent_msg_id': parent_msg_id,
                'subtype_xmlid': 'mail.mt_comment',
                'parent_id': parent_id.id if parent_id else None
            }

            if message_type == 'text':
                kwargs['body'] = plaintext2html(message['text']['body'])

            elif message_type in ('document', 'image', 'audio', 'video', 'sticker'):
                media = message[message_type]
                filename = media.get('filename')
                is_voice = media.get('voice')
                mime_type = media.get('mime_type')
                caption = media.get('caption')
                document_id = media['id']
                headers = {"Authorization": f"Bearer {self.access_token}"}

                response = self.env['whatsapp.api.services'].get_request(
                    f"{document_id}",
                    headers=headers
                )
                file_url = response.get('url')
                response_url = self.env['whatsapp.api.services'].get_request(
                    file_url,
                    headers=headers,
                    endpoint_include=True,
                    response_only=True
                )
                datas = response_url.content
                if not filename:
                    extension = mimetypes.guess_extension(mime_type) or ''
                    filename = message_type + extension
                kwargs['attachments'] = [(filename, datas, {'voice': is_voice})]
                if caption:
                    kwargs['body'] = plaintext2html(caption)

            elif message_type == 'reaction':
                msg_uid = message['reaction'].get('message_id')
                whatsapp_message = self.env['whatsapp.message.info'].sudo().search([('message_id', '=', msg_uid)])
                if whatsapp_message:
                    partner_id = channel.whatsapp_partner_id
                    emoji = message['reaction'].get('emoji')
                    whatsapp_message.mail_message_id._post_whatsapp_reaction(reaction_content=emoji,
                                                                             partner_id=partner_id)
                    continue

            else:
                _logger.warning("Unsupported whatsapp message type: %s", message)
                continue
            channel.message_post(whatsapp_inbound_msg_uid=message['id'], **kwargs)
