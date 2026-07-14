from odoo import api, fields, models

class WhatsappAPILog(models.Model):
    _name = 'whatsapp.api.log'
    _description = 'API Log'

    name = fields.Char()
    error_msg = fields.Text()
