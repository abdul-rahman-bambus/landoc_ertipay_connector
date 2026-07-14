from odoo import fields, models, api


class PropertyType(models.Model):
    _name = 'property.type'
    _description = 'Property Type Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", tracking=1, required=True)
    service_category_id = fields.Many2one(comodel_name="product.category", tracking=1, string="Category of Service", domain=[('is_propertychecklist_needed', '=', True)])
    checklist_line = fields.One2many(comodel_name='property.type.line',
        inverse_name='property_type_id',string="Checklist Data")
    company_id = fields.Many2one(comodel_name='res.company', tracking=1, index=True)


class PropertyTypeLine(models.Model):
    _name = 'property.type.line'
    _description = 'Property Type Line'

    name = fields.Char(string="Name")
    property_type_id = fields.Many2one(comodel_name="property.type")
    is_data_required = fields.Boolean(string="Data")
    is_attachment_required = fields.Boolean(string="Attachment")
    company_id = fields.Many2one(comodel_name='res.company',index=True)

