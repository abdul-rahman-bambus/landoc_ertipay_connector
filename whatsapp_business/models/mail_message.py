from odoo import fields, models, api
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = 'mail.message'

    message_type = fields.Selection(
        selection_add=[('whatsapp_message', 'WhatsApp')],
        ondelete={'whatsapp_message': lambda recs: recs.write({'message_type': 'comment'})},
    )
    wa_message_ids = fields.One2many(
        'whatsapp.message.info',
        'mail_message_id',
        string='Related WhatsApp Messages'
    )

    def _post_whatsapp_reaction(self, reaction_content, partner_id):
        """Post or update a WhatsApp reaction for a message."""
        self.ensure_one()
        # Remove existing reaction from this partner, if any
        existing_reaction = self.reaction_ids.filtered(lambda r: r.partner_id == partner_id)
        if existing_reaction:
            content = existing_reaction.content
            existing_reaction.unlink()
            self._bus_send_reaction_group(content)
        # Add new reaction if provided
        if reaction_content and self.id:
            self.env['mail.message.reaction'].create({
                'message_id': self.id,
                'content': reaction_content,
                'partner_id': partner_id.id,
            })
            self._bus_send_reaction_group(reaction_content)

    def _to_store(self, store: Store, **kwargs):
        """Add WhatsApp message status to the store for discuss rendering."""
        super()._to_store(store, **kwargs)
        whatsapp_msgs = self.filtered(lambda m: m.message_type == "whatsapp_message")
        if whatsapp_msgs:
            whatsapp_infos = self.env["whatsapp.message.info"].sudo().search([
                ("mail_message_id", "in", whatsapp_msgs.ids)
            ])
            for whatsapp_message in whatsapp_infos:
                store.add(
                    whatsapp_message.mail_message_id,
                    {"whatsappStatus": whatsapp_message.state}
                )
