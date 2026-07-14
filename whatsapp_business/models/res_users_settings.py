from odoo import fields, models, api

class ResUsersSettings(models.Model):
    _inherit = 'res.users.settings'

    is_discuss_sidebar_category_whatsapp_business_open = fields.Boolean(
        string='WhatsApp Sidebar Open', default=True,
        help="If checked, the WhatsApp category is open in the discuss sidebar")

