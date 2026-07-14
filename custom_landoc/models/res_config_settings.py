from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    landoc_vendor_id = fields.Many2one('res.partner')
    no_witness = fields.Integer(string='No of Witnesses', default=2)
    government_link = fields.Char("Government Link")
    department_id = fields.Many2one(
        'crm.team', string='Department', ondelete="set null", readonly=False, store=True)
    bot_user_id = fields.Many2one('res.users', ondelete="set null", readonly=False, store=True)
    responsible_user_id = fields.Many2one('res.users', ondelete="set null", readonly=False, store=True)

    @api.model
    def get_values(self):
        """Load saved config values into the settings form"""
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            landoc_vendor_id=int(params.get_param('custom_landoc.landoc_vendor_id')) or False,
            no_witness=int(params.get_param('custom_landoc.no_witness')) or 2,
            government_link=params.get_param('custom_landoc.government_link') or False,
            department_id=int(params.get_param('custom_landoc.department_id')) or False,
            bot_user_id=int(params.get_param('custom_landoc.bot_user_id')) or False,
            responsible_user_id=int(params.get_param('custom_landoc.responsible_user_id')) or False,
        )
        return res

    def set_values(self):
        """Save values from the settings form into system parameters"""
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('custom_landoc.landoc_vendor_id', self.landoc_vendor_id.id or False)
        params.set_param('custom_landoc.no_witness', self.no_witness or 2)
        params.set_param('custom_landoc.government_link', self.government_link or False)
        params.set_param('custom_landoc.department_id', self.department_id.id or False)
        params.set_param('custom_landoc.bot_user_id', self.bot_user_id.id or False)
        params.set_param('custom_landoc.responsible_user_id', self.responsible_user_id.id or False)
