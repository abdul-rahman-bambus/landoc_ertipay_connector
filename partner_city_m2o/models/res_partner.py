from odoo import models, fields, api

class ResCity(models.Model):
    _name = "res.city"
    _description = "City"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("City Name", required=True, index=True, tracking=1)
    state_id = fields.Many2one("res.country.state", string="State", tracking=1, required=True, domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one("res.country", string="Country", tracking=1, required=True)
    company_id = fields.Many2one(comodel_name='res.company', tracking=1, index=True)

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id and self.country_id != self.state_id.country_id:
            self.state_id = False

    @api.onchange('state_id')
    def _onchange_state(self):
        if self.state_id.country_id and self.country_id != self.state_id.country_id:
            self.country_id = self.state_id.country_id


class ResPartner(models.Model):
    _inherit = "res.partner"

    city_id = fields.Many2one("res.city", string="City ", tracking=1)
    religion_id = fields.Many2one('res.religion', string="Religion", tracking=1)

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id and self.country_id != self.state_id.country_id:
            self.city_id = False
            self.state_id = False

    @api.onchange('state_id')
    def _onchange_state(self):
        if self.state_id.country_id and self.country_id != self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id.state_id and self.city_id.state_id != self.state_id:
            self.state_id = self.city_id.state_id
            self.country_id = self.city_id.country_id


class ResCompany(models.Model):
    _inherit = "res.company"

    city_id = fields.Many2one("res.city", string="City ", tracking=1)
    city = fields.Char(related="city_id.name", readonly=True)

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id and self.country_id != self.state_id.country_id:
            self.city_id = False
            self.state_id = False

    @api.onchange('state_id')
    def _onchange_state(self):
        if self.state_id.country_id and self.country_id != self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id.state_id and self.city_id.state_id != self.state_id:
            self.state_id = self.city_id.state_id
            self.country_id = self.city_id.country_id

