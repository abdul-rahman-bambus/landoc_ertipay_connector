from odoo import _, api, fields, models

class ResUsers(models.Model):
    _name = "res.trans.lang"
    _description = "Translation Language"

    name = fields.Char("Language")
    code = fields.Char("Code")