from odoo import fields, models, api, _
from odoo.exceptions import (
    UserError, ValidationError
)


class LandocFees(models.Model):
    _name = 'landoc.fees'
    _description = 'Landoc Fees'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(tracking=1)
    service_category_id = fields.Many2one(comodel_name="product.category", domain="[('is_service','=',True)]",
                                          required=True,
                                          tracking=1, string="Category of Service")
    service_id = fields.Many2one(comodel_name="service.type",
                                 domain="[('service_category_id','=',service_category_id)]", tracking=1, required=True,
                                 string="Service")
    service_count = fields.Integer()
    customer_fees_line = fields.One2many(comodel_name="landoc.customer.fees", inverse_name="fees_id")
    vendor_fees_line = fields.One2many(comodel_name="landoc.vendor.fees", inverse_name="fees_id")
    is_govt_online_payment_required = fields.Boolean(string="Govt Online Payment Required")
    is_ec = fields.Boolean(compute='_compute_is_ec')
    currency_id = fields.Many2one('res.currency', string='Landoc Fee Currency',
                                  required=True,
                                  default=lambda self: self.env.company.currency_id.id)
    customer_fee_total = fields.Monetary(compute='_compute_total_fees', currency_field='currency_id')
    vendor_fee_total = fields.Monetary(compute='_compute_total_fees', currency_field='currency_id')

    ################
    # Compute
    ################

    @api.depends('customer_fees_line', 'vendor_fees_line')
    def _compute_total_fees(self):
        for record in self:
            record.customer_fee_total = sum(record.customer_fees_line.mapped('rate_total'))
            record.vendor_fee_total = sum(record.vendor_fees_line.mapped('rate_total'))

    @api.depends('service_id')
    def _compute_is_ec(self):
        """
        To compute EC boolean
        """
        for record in self:
            if record.service_id.service_type == 'encumbrance_certificate':
                record.is_ec = True
            else:
                record.is_ec = False

    ###########
    # Onchange
    ###########

    @api.onchange('service_id')
    def onchange_service_id_method(self):
        if self.service_id and self.search_count([('service_id', '=', self.service_id.id)]) >=1:
            raise UserError(_(f'Service {self.service_id.name} already exists.'))

    @api.onchange('service_category_id')
    def onchange_service_category_id_method(self):
        self.service_id = False
        self.customer_fees_line = False
        self.customer_fees_line = False

        if self.service_category_id:
            service_type = self.env['service.type'].search([('service_category_id','=',self.service_category_id.id)])
            self.service_id = service_type[0] if len(service_type.ids) == 1 else False
            self.service_count = len(service_type)



class LandocCustomerFees(models.Model):
    _name = 'landoc.customer.fees'
    _description = 'Landoc Customer Fees'

    fees_id = fields.Many2one(comodel_name="landoc.fees")
    product_id = fields.Many2one(comodel_name="product.product")
    ec_customer_fee_category = fields.Selection([('govt_fees', 'Government Fees'), ], string="EC Fees Category")
    currency_id = fields.Many2one('res.currency', string='Customer Fees Currency',
                                  required=True,
                                  default=lambda self: self.env.company.currency_id.id)
    rate = fields.Monetary(currency_field='currency_id')
    tax_excluded_amount = fields.Monetary(currency_field='currency_id', compute='_compute_rate_total')
    rate_total = fields.Monetary(currency_field='currency_id', string="Total", compute='_compute_rate_total')
    tax_ids = fields.Many2many('account.tax', 'landoc_customer_taxes_rel', 'prod_id', 'tax_id',
                                string="Sales Taxes",
                                help="Default taxes used in Quotations",
                                domain=[('type_tax_use', '=', 'sale')],
                                default=lambda
                                    self: self.env.companies.account_sale_tax_id or self.env.companies.root_id.sudo().account_sale_tax_id,
                                )

    @api.depends('rate', 'tax_ids')
    def _compute_rate_total(self):
        for record in self:
            taxes = record.tax_ids.compute_all(
                record.rate,
                currency=record.currency_id,
                quantity=1.0,
            )
            record.tax_excluded_amount = taxes['total_included'] - taxes['total_excluded']
            record.rate_total = taxes['total_included']


class LandocVendorFees(models.Model):
    _name = 'landoc.vendor.fees'
    _description = 'Landoc Vendor Fees'

    fees_id = fields.Many2one(comodel_name="landoc.fees")
    product_id = fields.Many2one(comodel_name="product.product")
    ec_category = fields.Selection([])
    ec_vendor_fee_category = fields.Selection([('application_fee', 'Application Fee'), ('search_fee_1st_year', 'Search Fee 1st Year'),
                       ('search_fee_additional_year', 'Search Fee for Additional Year'), ('computer_fees', 'Computer Fees'),], string="EC Fees Category")
    currency_id = fields.Many2one('res.currency', string='Vendor Fees Currency',
                                  required=True,
                                  default=lambda self: self.env.company.currency_id.id)
    rate = fields.Monetary(currency_field='currency_id')
    tax_excluded_amount = fields.Monetary(currency_field='currency_id', compute='_compute_rate_total')
    rate_total = fields.Monetary(currency_field='currency_id', string="Total", compute='_compute_rate_total')
    tax_ids = fields.Many2many('account.tax', 'landoc_vendor_taxes_rel', 'prod_id', 'tax_id',
                                         string="Vendor Taxes",
                                         help="Default taxes used in Vendors",
                                         domain=[('type_tax_use', '=', 'purchase')],
                                         default=lambda
                                             self: self.env.companies.account_purchase_tax_id or self.env.companies.root_id.sudo().account_purchase_tax_id,
                                         )

    @api.depends('rate', 'tax_ids')
    def _compute_rate_total(self):
        for record in self:
            taxes = record.tax_ids.compute_all(
                record.rate,
                currency=record.currency_id,
                quantity=1.0,
            )
            record.tax_excluded_amount = taxes['total_included'] - taxes['total_excluded']
            record.rate_total = taxes['total_included']
