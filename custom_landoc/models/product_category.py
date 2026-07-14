from odoo import fields, models, api


class ProductCategory(models.Model):
    _inherit = 'product.category'

    is_service = fields.Boolean(string="Service", tracking=1)
    workflow_master_id = fields.Many2one(comodel_name="workflow.master", string="Workflow Master")
    is_propertychecklist_needed = fields.Boolean(string="Property Checklist Needed", tracking=1)
    is_marriage_category = fields.Boolean(string="Marriage Registraion", tracking=1)

    @api.depends('name')
    @api.depends_context('calling_model')
    def _compute_display_name(self):
        for category in self:
            calling_model = self.env.context.get('calling_model')

            if calling_model == 'crm.lead':
                category.display_name = category.name
            else:
                category.display_name = category.complete_name
