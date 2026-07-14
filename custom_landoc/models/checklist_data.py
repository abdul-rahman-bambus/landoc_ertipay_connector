from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class ChecklistData(models.Model):
    _name = 'checklist.data'
    _description = 'Checklist Data'
    _rec_name = "name"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Description", tracking=1)
    service_category_id = fields.Many2one(comodel_name="product.category", domain="[('is_service','=',True)]",
                                          tracking=1, string="Category of Service")
    service_id = fields.Many2one(comodel_name="service.type",
                                 domain="[('service_category_id','=',service_category_id)]", tracking=1,
                                 string="Service")
    checklist_type = fields.Selection(selection=[('service','Service'), ('content','Content')], tracking=1, string="Type", copy=False, index=True)
    checklist_data_ids = fields.One2many(comodel_name='field.data',
        inverse_name='checklist_data_id',string="Checklist Data")
    company_id = fields.Many2one(comodel_name='res.company', tracking=1, index=True)

