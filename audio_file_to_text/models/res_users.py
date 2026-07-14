from odoo import _, api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    voice_to_text_lang_id = fields.Many2one("res.trans.lang","Voice Translation Language")
