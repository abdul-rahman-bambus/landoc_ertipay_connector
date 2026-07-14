from odoo import fields, models, api, _
from odoo.exceptions import (
    UserError, ValidationError,
)
import re
import phonenumbers


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _rec_names_search = ['complete_name', 'email', 'mobile', 'phone', 'ref', 'vat', 'company_registry']

    # religion_id = fields.Many2one('res.religion', string="Religion")
    mobile = fields.Char(string="Whatsapp No ", required=True, tracking=1)
    phone = fields.Char(string="Mobile", tracking=1)
    city = fields.Char(related="city_id.name", readonly=True)

    @api.depends('complete_name', 'email', 'mobile', 'phone', 'vat', 'state_id', 'country_id', 'commercial_company_name')
    @api.depends_context('show_address', 'partner_show_db_id', 'address_inline', 'show_email', 'show_vat', 'lang')
    def _compute_display_name(self):
        for partner in self:
            valid_mobile = self.get_valid_number(partner.mobile)

            name = f"{partner.name}, {partner.mobile}" if partner.mobile else partner.with_context(lang=self.env.lang)._get_complete_name()
            if partner._context.get('show_address'):
                name = name + "\n" + partner._display_address(without_company=True)
            name = re.sub(r'\s+\n', '\n', name)
            if partner._context.get('partner_show_db_id'):
                name = f"{name} ({partner.id})"
            if partner._context.get('address_inline'):
                splitted_names = name.split("\n")
                name = ", ".join([n for n in splitted_names if n.strip()])
            if partner._context.get('show_email') and partner.email:
                name = f"{name} <{partner.email}>"
            if partner._context.get('show_vat') and partner.vat:
                name = f"{name} ‒ {partner.vat}"

            partner.display_name = name.strip()

    def get_valid_number(self, mobile):
        try:
            number = phonenumbers.parse(mobile)
            country_code = number.country_code
            if country_code:
                return mobile
        except Exception as e:
            return False

    # @api.constrains('mobile')
    # def mobile_whatsapp_validation(self):
    #     valid_mobile = self.get_valid_number(self.mobile)
    #     if not self._context.get('from_user_creation') and not valid_mobile:
    #         raise ValidationError('Kindly provide a valid WhatsApp number, ensuring that it includes the correct "country code".')



class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        """To extend users and partner default values."""
        country_id = self.env.ref('base.in')
        for user in vals_list:
            user['mobile'] = f"+{country_id.phone_code} "
            user['country_id'] = country_id.id
        return super(ResUsers, self.with_context(from_user_creation=True)).create(vals_list)
