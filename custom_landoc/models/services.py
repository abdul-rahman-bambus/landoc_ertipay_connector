from odoo import fields, models, api

SERVICE_TYPES = [
    ('certified_copy', 'Certified Copy'),
    ('document_consulting', 'Document Consulting'),
    ('document_registration', 'Document Registration'),
    ('encumbrance_certificate', 'Encumbrance Certificate'),
    ('legal_opinion', 'Legal Opinion'),
    ('land_surveying', 'Land Surveying'),
    ('marriage_registration', 'Marriage Registration'),
    ('revenue_and_local_body_department_works', 'Revenue & Local Body Department Works'),
    ('stamp_paper', 'Stamp Paper'),
    ('unregistered_agreement', 'Unregistered Agreement'),
    ('unregistered_agreement_others', 'Unregistered Agreement (Others)'),
]


class ServiceType(models.Model):
    _name = 'service.type'
    _description = 'Service Type'
    _rec_name = "name"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Service", tracking=1)
    code = fields.Char(string="Code")
    service_category_id = fields.Many2one('product.category', tracking=1, domain="[('is_service','=',True)]", required=True, string="Service Category")
    company_id = fields.Many2one(comodel_name='res.company', tracking=1, index=True)
    fees_above_ninety = fields.Float(string="Fees Above Ninety", tracking=1)
    fees_above_one_hundred_fifty = fields.Float(string="Fees Above One Hundred Fifty", tracking=1)
    service_type = fields.Selection(selection=SERVICE_TYPES, required=True, tracking=1)
    religion = fields.Selection(selection=[('hindu', 'Hindu Marriage'), ('muslim', 'Muslim Marriage'), ('christian', 'Christian Marriage'), ('tamilnadu', 'TN Marriage'), ('special', 'Special Marriage')], required=True, tracking=1)

    vendor_products_ids = fields.Many2many(comodel_name='product.product', domain="[('type','=', 'service'), ('purchase_ok','=',True)]")


    @api.onchange('name')
    def onchange_compute_code(self):
        for service in self:
            service_code = service.name.replace(" ", "_") if service.name else service.name
            service.code = service_code.lower() if service_code else False
