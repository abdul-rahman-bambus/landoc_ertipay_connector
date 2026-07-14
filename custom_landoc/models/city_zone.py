from odoo import models, fields

class Division(models.Model):
    _name = "res.district"
    _description = "District"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="District Name", tracking=1, required=True)
    zone_id = fields.Many2one('res.zone', tracking=1, string="Zone", required=True)
    company_id = fields.Many2one(comodel_name='res.company', tracking=1, index=True)

class Village(models.Model):
    _name = "res.village"
    _description = "Village"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Village Name", tracking=1, required=True)
    start_date = fields.Date(string='Start Date', tracking=1)
    end_date = fields.Date(string='End Date', tracking=1)
    sro_id = fields.Many2one('res.sro', string="Sub Registrar Office", tracking=1, required=True)
    company_id = fields.Many2one(comodel_name='res.company', tracking=1, index=True)
    district_id = fields.Many2one(related='sro_id.district_id', tracking=1, store=True)
    zone_id = fields.Many2one(related='district_id.zone_id', tracking=1, store=True)


class Zone(models.Model):
    _name = "res.zone"
    _description = "Zone"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Zone Name", tracking=1, required=True)
    company_id = fields.Many2one(comodel_name='res.company', tracking=1, index=True)
    

