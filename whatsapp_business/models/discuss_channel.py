from odoo import fields, Command, models, api, tools, _
# from odoo.fields import Command
from odoo.addons.mail.tools.discuss import Store
from markupsafe import Markup
from odoo.exceptions import ValidationError
from bs4 import BeautifulSoup
from datetime import timedelta


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    channel_type = fields.Selection(
        selection_add=[('whatsapp', 'WhatsApp Conversation')],
        ondelete={'whatsapp': 'cascade'})
    whatsapp_number = fields.Char(string="Phone Number")
    whatsapp_channel_valid_until = fields.Datetime(string="WhatsApp Channel Valid Until Datetime",
                                                   compute="_compute_whatsapp_channel_valid_until")
    last_wa_mail_message_id = fields.Many2one(comodel_name="mail.message", string="Last WA Partner Mail Message",
                                              index='btree_not_null')
    whatsapp_partner_id = fields.Many2one(comodel_name='res.partner', string="WhatsApp Partner", index='btree_not_null')
    account_id = fields.Many2one(comodel_name='whatsapp.account.details', string="WhatsApp Business Account")
    # whatsapp_channel_active = fields.Boolean('Is Whatsapp Channel Active', compute="_compute_whatsapp_channel_active")

    @api.depends('last_wa_mail_message_id')
    def _compute_whatsapp_channel_valid_until(self):
        for channel in self:
            channel.whatsapp_channel_valid_until = channel.last_wa_mail_message_id.create_date + timedelta(hours=24) \
                if channel.channel_type == "whatsapp" and channel.last_wa_mail_message_id else False

    @api.model
    def create_whatsapp_channel(self, whatsapp_number, wa_account_id, sender_name=None, create_if_not_found=False):
        """
        Create or return a WhatsApp discuss channel.
        :param whatsapp_number: E.164 format number (e.g., +918281234567)
        :param wa_account_id: whatsapp.account record
        :param sender_name: optional sender name
        :param create_if_not_found: flag to allow creation
        """
        formatted_number = whatsapp_number if whatsapp_number.startswith('+') else f'+{whatsapp_number}'
        clean_number = formatted_number.lstrip('+')

        domain = [('whatsapp_number', '=', formatted_number), ('account_id', '=', wa_account_id.id)]
        channel = self.sudo().search(domain, order='create_date desc', limit=1)
        partners_to_notify = wa_account_id.notify_users_ids.mapped('partner_id')

        if not channel and create_if_not_found:
            partner = self.env['res.partner']._find_or_create_from_number(formatted_number, sender_name)
            if partner:
                name = partner.name
            elif sender_name:
                name = sender_name
            else:
                name = formatted_number
            channel = self.sudo().create({
                'name': name,
                'channel_type': 'whatsapp',
                'whatsapp_number': formatted_number,
                'whatsapp_partner_id': partner.id,
                'account_id': wa_account_id.id,
                'channel_member_ids': [Command.create({'partner_id': partner.id})],
            })
            channel.channel_member_ids = [Command.clear()] + [Command.create({'partner_id': partner.id}) for partner in
                                                              partners_to_notify]

            channel._bus_send(
                "discuss.channel.member/fetched",
                {
                    "channel_id": channel.id,
                },
            )
            channel._broadcast(partner.ids)
        return channel

    def message_post(self, *, message_type='notification', **kwargs):
        new_msg = super().message_post(message_type=message_type, **kwargs)
        message_log = self.env['whatsapp.message.info']
        if self.channel_type == 'whatsapp' and message_type == 'whatsapp_message':
            if new_msg.author_id == self.whatsapp_partner_id:
                self.last_wa_mail_message_id = new_msg

            if not new_msg.wa_message_ids:
                text_formated = self.html_to_whatsapp_text(str(new_msg.body))
                message_instance = message_log.create({
                    'mobile_number': self.whatsapp_number,
                    'mail_message_id': new_msg.id,
                    'message_type': 'outbound',
                    'account_id': self.account_id.id,
                    'message_body': text_formated,
                })
                message_log._send(self.whatsapp_number, message_instance=message_instance, messge_body=new_msg.body, wh_account=self.account_id)
        return new_msg

    def html_to_whatsapp_text(self, html):
        """Replace <br> with newline before parsing"""
        html = html.replace("<br>", "\n").replace("<br/>", "\n")
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text()

    def _get_notify_valid_parameters(self):
        if self.channel_type == 'whatsapp':
            return super()._get_notify_valid_parameters() | {'whatsapp_inbound_msg_uid'}
        return super()._get_notify_valid_parameters()

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        """Notify thread and log inbound WhatsApp messages if applicable."""
        parent_msg_id = kwargs.pop('parent_msg_id', False)
        recipients_data = super()._notify_thread(message, msg_vals=msg_vals, **kwargs)

        whatsapp_uid = kwargs.get('whatsapp_inbound_msg_uid')
        if whatsapp_uid and self.channel_type == 'whatsapp':
            text_formatted = self.html_to_whatsapp_text(str(message.body))
            whatsapp_message = {
                'mail_message_id': message.id,
                'message_type': 'inbound',
                'mobile_number': self.whatsapp_number,
                'message_id': whatsapp_uid,
                'message_body': text_formatted,
                'parent_id': parent_msg_id,
                'state': 'received',
                'account_id': self.account_id.id,
            }
            self.env['whatsapp.message.info'].create(whatsapp_message)
            if parent_msg_id:
                parent_msg = self.env['whatsapp.message.info'].browse(parent_msg_id)
                parent_msg.state = 'replied'
        return recipients_data

    def whatsapp_channel_join_and_pin(self):
        """
        Adds the current partner as a member of self channel and pins them if not already pinned.
        Only applicable for WhatsApp channels.
        """
        self.ensure_one()
        if self.channel_type != 'whatsapp':
            raise ValidationError(_('This join method is not possible for regular channels.'))

        self.check_access('write')
        current_partner = self.env.user.partner_id
        member = self.channel_member_ids.filtered(lambda m: m.partner_id == current_partner)

        if member:
            if not member.is_pinned:
                member.write({'unpin_dt': False})
            return Store(self).get_result()

        # Add new member and notify
        new_member = self.env['discuss.channel.member'].with_context(
            tools.clean_context(self.env.context)
        ).sudo().create([{
            'partner_id': current_partner.id,
            'channel_id': self.id,
        }])
        message_body = Markup(f'<div class="o_mail_notification">{_("joined the channel")}</div>')
        new_member.channel_id.message_post(
            body=message_body,
            message_type="notification",
            subtype_xmlid="mail.mt_comment"
        )
        self._bus_send_store(Store(new_member).add(self, {"memberCount": self.member_count}))
        return Store(self).get_result()
