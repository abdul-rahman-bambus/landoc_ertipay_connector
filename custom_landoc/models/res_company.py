from odoo import api, fields, models, tools, _, Command, SUPERUSER_ID


class ResCompanies(models.Model):
    _inherit = 'res.company'

    sro_ids = fields.Many2many(comodel_name="res.sro", tracking=1, string="SRO")
    sro_ids_compute = fields.Many2many(comodel_name="res.sro", tracking=1, compute="compute_sro_ids")
    zone_ids = fields.Many2many(comodel_name="res.zone", tracking=1, string="Zone")

    @api.depends('zone_ids')
    def compute_sro_ids(self):
        for rec in self:
            district_sro_ids = self.env['res.district'].search([('zone_id', 'in', rec.zone_ids.ids)])
            zone_sro_ids = self.env['res.sro'].search([('district_id', 'in', district_sro_ids.ids)])
            rec.sro_ids_compute = zone_sro_ids.ids

    @api.onchange('zone_ids')
    def onchange_zone_ids(self):
        self.sro_ids = False

    @api.model_create_multi
    def create(self, vals_list):
        """
            FYI: For res.partner creation mobile number mandatory, so inherited to extending create arguments.
        """
        # create missing partners
        no_partner_vals_list = [
            vals
            for vals in vals_list
            if vals.get('name') and not vals.get('partner_id')
        ]
        if no_partner_vals_list:
            # -------------- Altered code starts ------------------#
            partners = self.env['res.partner'].with_context(default_parent_id=False).create([
                {
                    'name': vals['name'],
                    'is_company': True,
                    'image_1920': vals.get('logo'),
                    'email': vals.get('email'),
                    'phone': vals.get('phone'),
                    'mobile': vals.get('mobile'), # Added Mobile number.
                    'website': vals.get('website'),
                    'vat': vals.get('vat'),
                    'country_id': vals.get('country_id'),
                }
                for vals in no_partner_vals_list
            ])
            # ------------------- Ends ---------------------------#
            # compute stored fields, for example address dependent fields
            partners.flush_model()
            for vals, partner in zip(no_partner_vals_list, partners):
                vals['partner_id'] = partner.id

        for vals in vals_list:
            # Copy delegated fields from root to branches
            if parent := self.browse(vals.get('parent_id')):
                for fname in self._get_company_root_delegated_field_names():
                    vals.setdefault(fname, self._fields[fname].convert_to_write(parent[fname], parent))

        self.env.registry.clear_cache()
        companies = super().create(vals_list)

        # The write is made on the user to set it automatically in the multi company group.
        if companies:
            (self.env.user | self.env['res.users'].browse(SUPERUSER_ID)).write({
                'company_ids': [Command.link(company.id) for company in companies],
            })

        # Make sure that the selected currencies are enabled
        companies.currency_id.sudo().filtered(lambda c: not c.active).active = True

        companies_needs_l10n = companies.filtered('country_id')
        if companies_needs_l10n:
            companies_needs_l10n.install_l10n_modules()

        return companies
