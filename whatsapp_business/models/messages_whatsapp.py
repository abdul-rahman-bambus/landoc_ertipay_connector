from odoo import models, fields, api, _
import json
import logging
from bs4 import BeautifulSoup
import base64
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

class WhatsAppMessage(models.Model):
    _name = 'whatsapp.message.info'
    _description = 'WhatsApp Message'

    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user)
    mobile_number = fields.Char(string='Mobile Number', required=True)
    formated_mobile_number = fields.Char(string='Formated Mobile Number')
    template_id = fields.Many2one('template.whatsapp', string='Template')
    message_body = fields.Text(string='Message Body')
    account_id = fields.Many2one(comodel_name='whatsapp.account.details', string="WhatsApp Business Account")
    parent_id = fields.Many2one('whatsapp.message.info', 'Response To', ondelete="set null")
    message_id = fields.Char(string="WhatsApp Message ID")
    mail_message_id = fields.Many2one(comodel_name='mail.message', index=True)
    message_type = fields.Selection([
        ('outbound', 'Outgoing'),
        ('inbound', 'Incoming')], string="Message Type", default='outbound')
    state = fields.Selection([
        ('outgoing', 'In Queue'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('received', 'Received'),
        ('error', 'Failed'),
        ('bounced', 'Bounced'),
        ('cancel', 'Cancelled')], string='Status', default='outgoing')
    failure_reason = fields.Text(string='Failure Reason', help='Reason for message failure, if any.')
    failure_state = fields.Selection([
        ('invalid_number', 'Invalid Number'),
        ('template_not_approved', 'Template Not Approved'),
        ('api_error', 'API Error'),
        ('other', 'Other'),
    ], string='Failure Type', help='Type of failure if the message was not sent successfully.')

    _SUPPORTED_ATTACHMENT_TYPE = {
        'audio': ('audio/aac', 'audio/mp4', 'audio/mpeg', 'audio/amr', 'audio/ogg'),
        'document': (
            'text/plain', 'application/pdf', 'application/vnd.ms-powerpoint', 'application/msword',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ),
        'image': ('image/jpeg', 'image/png'),
        'video': ('video/mp4',),
    }

    def _process_statuses(self, value):
        """ Process status of the message like 'send', 'delivered' and 'read'."""
        mapping = {'failed': 'error', 'cancelled': 'cancel'}
        processed_message_ids = set()
        for statuses in value.get('statuses', []):
            whatsapp_message = self.env['whatsapp.message.info'].sudo().search([('message_id', '=', statuses['id'])])
            if whatsapp_message:
                whatsapp_message.state = mapping.get(statuses['status'], statuses['status'])
                processed_message_ids.add(whatsapp_message.id)
                whatsapp_message._update_message_fetched_seen()
                if statuses['status'] == 'failed':
                    error = statuses['errors'][0] if statuses.get('errors') else None
                    if error:
                        log_instance = self.env['whatsapp.api.log']
                        log_instance.sudo().create({'name': error['code'], "error_msg": f"{error['code']} : {error['title']}"})
        return self.env['whatsapp.message.info'].browse(sorted(processed_message_ids, reverse=True)).sudo()

    def _update_message_fetched_seen(self):
        """Update message status for the WhatsApp recipient."""
        self.ensure_one()
        # Only process messages related to discuss channels
        if self.mail_message_id.model != 'discuss.channel':
            return

        channel = self.env['discuss.channel'].browse(self.mail_message_id.res_id)
        channel_members = channel.channel_member_ids
        if not channel_members:
            return

        channel_member = channel_members[0]
        notification_type = None

        if self.state == 'read':
            # Update fetched and seen message IDs, and last seen datetime
            fetched_id = max(
                channel_member.fetched_message_id.id or 0,
                self.mail_message_id.id or 0
            )
            channel_member.write({
                'fetched_message_id': fetched_id,
                'seen_message_id': self.mail_message_id.id,
                'last_seen_dt': fields.Datetime.now(),
            })
            notification_type = 'discuss.channel.member/seen'
        elif self.state == 'delivered':
            # Only update fetched message ID
            channel_member.write({'fetched_message_id': self.mail_message_id.id})
            notification_type = 'discuss.channel.member/fetched'

        if notification_type:
            # Send bus notification to update UI or listeners
            channel._bus_send(
                notification_type,
                {
                    "channel_id": channel.id,
                    "id": channel_member.id,
                    "last_message_id": self.mail_message_id.id,
                    "partner_id": channel.whatsapp_partner_id.id,
                },
            )

    def _upload_whatsapp_document(self, attachment):
        """Upload message document for template registration."""
        phone_number_id = self.account_id.phone_number_id
        access_token = self.account_id.access_token
        file_data = base64.b64decode(attachment.raw) if isinstance(attachment.raw, str) else attachment.raw
        files = [('file', (attachment.name, file_data, attachment.mimetype))]
        params = {'access_token': access_token, 'messaging_product': 'whatsapp'}

        _logger.info(
            "Open template sample document upload session with file size %s Bytes of mimetype %s on account %s [%s]",
            attachment.file_size, attachment.mimetype, self.account_id.name, self.account_id.id
        )

        uploads_media = self.env['whatsapp.api.services'].send_request(
            f"{phone_number_id}/media", params=params, files=files
        )
        upload_session_id = uploads_media.get('id')
        if not upload_session_id:
            raise UserError(_("File uploading failed, please retry after sometime."))
        _logger.info("File uploading successful using account %s [%s]", self.account_id.name, self.account_id.id)
        return upload_session_id

    @api.model
    def _prepare_attachment_vals(self, attachment, message_instance):
        """ Upload the attachment to WhatsApp and return prepared values to attach to the message. """
        whatsapp_media_type = next((
            media_type
            for media_type, mimetypes
            in self._SUPPORTED_ATTACHMENT_TYPE.items()
            if attachment.mimetype in mimetypes),
            False
        )

        if not whatsapp_media_type:
            message = _("Attachment mimetype is not supported by WhatsApp: %s.", attachment.mimetype)
            raise UserError(message)
        whatsapp_media_uid = message_instance._upload_whatsapp_document(attachment)

        vals = {
            'type': whatsapp_media_type,
            whatsapp_media_type: {'id': whatsapp_media_uid}
        }

        if whatsapp_media_type == 'document':
            vals[whatsapp_media_type]['filename'] = attachment.name
        return vals

    def _send(self, number, message_instance, messge_body, wh_account):
        data = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': number
        }
        if message_instance.message_type != "outbound":
            _logger.info("Message type in %s state so it will not sent.", message_instance.message_type)
            # continue

        text_formated = self.html_to_whatsapp_text(str(messge_body))
        if message_instance.mail_message_id.attachment_ids:
            attachment_vals = message_instance._prepare_attachment_vals(message_instance.mail_message_id.attachment_ids[0],
                                                                        message_instance=message_instance)
            message_type = attachment_vals.get('type')
            send_vals = attachment_vals.get(message_type)
            if message_instance.message_body:
                send_vals['caption'] = text_formated

        else:
            message_type = 'text'
            send_vals = {
                'preview_url': True,
                'body': text_formated,
            }
            

        # Tagging parent message id if parent message is available
        if message_instance.mail_message_id and message_instance.mail_message_id.parent_id:
            parent_id = message_instance.mail_message_id.parent_id.wa_message_ids
            if parent_id:
                parent_message_id = parent_id[0].message_id
                data.update({
                    'context': {
                        'message_id': parent_message_id
                    },
                })



        if message_type in ('template', 'text', 'document', 'image', 'audio', 'video'):
            data.update({
                'type': message_type,
                message_type: send_vals,
            })

        json_data = json.dumps(data)
        _logger.info("Send %s message from account %s [%s]", message_type, wh_account.name,
                     wh_account.id)
        headers = {"Authorization": f"Bearer {wh_account.access_token}", "Content-Type": "application/json"}
        response = self.env['whatsapp.api.services'].send_request(f"{wh_account.phone_number_id}/messages", data=json_data, headers=headers)
        if response and response.get('messages') and response.get('contacts'):
            formated_no_id = ''
            for contact in response.get('contacts'):
                formated_no_id = contact.get('wa_id')

            for res in response.get('messages'):
                if res.get('id'):
                    message_instance.write({
                        'message_id': res.get('id'),
                        'formated_mobile_number': formated_no_id,
                    })

    def html_to_whatsapp_text(self, html):
        """Replace <br> with newline before parsing"""
        html = html.replace("<br>", "\n").replace("<br/>", "\n")
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text()
    