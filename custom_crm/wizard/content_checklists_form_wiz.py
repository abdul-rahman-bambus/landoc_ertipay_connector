from odoo import api, models, fields, _


class ContentChecklistsWiz(models.TransientModel):
    _name = 'content.checklists.wiz'
    _description = 'Content Checklists Wiz'

    contact_name = fields.Char()
    title = fields.Many2one(comodel_name="res.partner.title")
    # Address fields
    street = fields.Char('Street', readonly=False, store=True)
    street2 = fields.Char('Street2', readonly=False, store=True)
    zip = fields.Char('Zip', change_default=True, readonly=False, store=True)
    city_id = fields.Many2one("res.city", string="City ", readonly=False,
                              store=True)
    city = fields.Char(string='City', related="city_id.name", readonly=True)
    state_id = fields.Many2one(
        "res.country.state", string='State', readonly=False, store=True,
        domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one(
        'res.country', string='Country', readonly=False, store=True)

    mobile = fields.Char(default="+91 ", string="Whatsapp No ", required=True)
    relation = fields.Selection(selection=[('w/o', 'W/o'), ('s/o', 'S/o'), ('d/o', 'D/o'), ('h/o', 'H/o'), ('c/o', 'C/o')])
    aadhaar_no = fields.Char(string="Aadhaar No.")
    to_whom = fields.Char(string="To Whom")
    aadhaar_front_attachment = fields.Binary(copy=False)
    aadhaar_front_file_name = fields.Char()
    aadhaar_back_attachment = fields.Binary(copy=False)
    aadhaar_back_file_name = fields.Char()
    attachments = fields.Binary(copy=False)
    file_name = fields.Char()
    checklist_line_id = fields.Many2one(comodel_name="checklist.input.line")
    company_id = fields.Many2one(comodel_name='res.company',index=True)

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

    def add_checklist_info(self):
        self.checklist_line_id.write({
            'contact_name': self.contact_name,
            'title': self.title,
            'aadhaar_no': self.aadhaar_no,
            'mobile': self.mobile,
            'relation': self.relation,
            'to_whom': self.to_whom,
            # 'company_id': self.company_id.id,
            'aadhaar_front_file_name': self.aadhaar_front_file_name,
            'aadhaar_front_attachment': self.aadhaar_front_attachment,
            'aadhaar_back_file_name': self.aadhaar_back_file_name,
            'aadhaar_back_attachment': self.aadhaar_back_attachment,
            'street': self.street,
            'street2': self.street2,
            'zip': self.zip,
            'city_id': self.city_id.id,
            'state_id': self.state_id.id,
            'country_id': self.country_id.id,
        })
