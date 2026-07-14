from odoo import fields, models, api, _
from odoo.exceptions import (
    UserError, ValidationError
)
import phonenumbers


class HrEmployees(models.Model):
    _inherit = 'hr.employee'

    def get_valid_number(self, mobile):
        try:
            number = phonenumbers.parse(mobile)
            country_code = number.country_code
            if country_code:
                return mobile
        except Exception as e:
            return False

    @api.constrains('mobile_phone')
    def mobile_whatsapp_validation(self):
        valid_mobile = self.get_valid_number(self.mobile_phone)
        if not valid_mobile:
            raise ValidationError(
                'Kindly provide a valid WhatsApp number, ensuring that it includes the correct "country code".')
