from odoo import fields, models, api, _
import logging
import re
from odoo.addons.phone_validation.tools import phone_validation

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _find_or_create_from_number(self, number, name=False):
        """Number should come currently from whatsapp and contain country info."""
        search_number = number if number.startswith('+') else f'+{number}'

        region_data = phone_validation.phone_get_region_data_for_number(search_number)
        number_country_code = region_data['code']
        number_national_number = str(region_data['national_number'])
        number_phone_code = int(region_data['phone_code'])

        partners = self._search_on_phone_mobile("=", search_number)
        if not partners:
            partners = self._search_on_phone_mobile("=like", number_national_number)

        if not partners:
            country = self.env['res.country'].search([('phone_code', '=', number_phone_code)])
            if len(country) > 1:
                country = country.filtered(lambda c: c.code.lower() == number_country_code.lower())

            partners = self.env['res.partner'].create({
                'country_id': country.id if country and len(country) == 1 else False,
                'mobile': search_number,
                'name': name or search_number,
            })
            partners._message_log(body=_("Partner created by incoming WhatsApp message."))
        return partners[0]

    def _search_on_phone_mobile(self, operator, number):
        """Find partners based on phone/mobile numbers."""
        assert operator in {'=', '=like'}
        number = number.strip()
        phone_fields = ['mobile', 'phone']
        pattern = r'[\s\\./\(\)\-]'
        sql_operator = "LIKE" if operator == "=like" else "="

        def _format_term(num):
            term = re.sub(pattern, '', num)
            return f'%{term}' if operator == "=like" else term

        if number.startswith(('+', '00')):
            term = _format_term(number[1 if number.startswith('+') else 2:])
            where_str = ' OR '.join(
                f"""partner.{field} IS NOT NULL AND (
                        REGEXP_REPLACE(partner.{field}, %s, '', 'g') {sql_operator} %s OR
                        REGEXP_REPLACE(partner.{field}, %s, '', 'g') {sql_operator} %s
                )""" for field in phone_fields
            )
            query = f"SELECT partner.id FROM {self._table} partner WHERE {where_str};"
            params = []
            for _ in phone_fields:
                params += [pattern, '00' + term, pattern, '+' + term]
            self._cr.execute(query, tuple(params))
        else:
            term = _format_term(number)
            where_str = ' OR '.join(
                f"(partner.{field} IS NOT NULL AND REGEXP_REPLACE(partner.{field}, %s, '', 'g') {sql_operator} %s)"
                for field in phone_fields
            )
            query = f"SELECT partner.id FROM {self._table} partner WHERE {where_str};"
            params = []
            for _ in phone_fields:
                params += [pattern, term]
            self._cr.execute(query, tuple(params))

        res = self._cr.fetchall()
        return self.browse([r[0] for r in res])
