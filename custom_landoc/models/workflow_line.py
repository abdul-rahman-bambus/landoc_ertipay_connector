from odoo import fields, models, api


class WorkFlowLine(models.Model):
    _name = 'workflow.line'
    _description = 'Work Flow Line'
    _rec_name = "landoc_stage"

    workflow_id = fields.Many2one(comodel_name="workflow.master")
    department_id = fields.Many2one(comodel_name="crm.team", string="Department")
    landoc_stage = fields.Char(string="Landoc Stage")
    stage_id = fields.Many2one(comodel_name="crm.stage", string="Stage")
    sequence = fields.Integer(string="Sequence", default=1, required=True, copy=False, readonly=False)
    default_workflow = fields.Boolean(string="Default Workflow")
    estimated_time = fields.Float(string="Estimated Time")
    company_id = fields.Many2one(comodel_name='res.company',index=True)


