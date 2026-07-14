from odoo import fields, models, api


class ChecklistIds(models.Model):
    _name = 'service.checklist'
    _description = 'Checklist Service'

    checklist_id = fields.Many2one(comodel_name="checklist.data", string="Checklist")
    no_of_occurrences = fields.Integer(string="No of Occurrences", default=1)
    workflow_master_id = fields.Many2one(comodel_name="workflow.master", string="Product Category")
    company_id = fields.Many2one(comodel_name='res.company',index=True)

