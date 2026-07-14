from odoo import fields, models, api, _


class WorkflowMaster(models.Model):
    _name = 'workflow.master'
    _description = 'Workflow Master'
    _rec_name = "name"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sequence = fields.Char(string="Sequence", required=True, copy=False, readonly=False,
                           default=lambda self: _('New'))
    name = fields.Char(string="Name", required=True, tracking=True)
    add_default_workflow = fields.Boolean(string="Add Default Workflow")
    workflow_ids = fields.One2many(comodel_name="workflow.line", inverse_name='workflow_id')
    category_id = fields.Many2one(comodel_name="product.category", tracking=True,
                                    domain="[('is_service','=',True)]",
                                    string="Category")
    checklist_ids = fields.One2many(comodel_name='service.checklist',
                                    inverse_name='workflow_master_id', string="Checklist")
    company_id = fields.Many2one(comodel_name='res.company', tracking=1, index=True)

    # EC
    is_ec_service = fields.Boolean(string="Is EC Service", tracking=True)
    ec_year_applicable = fields.Selection(selection=[('before_1975', 'Before 1975'),('after_1975', 'After 1975'),], tracking=True)

    # CC
    book_03_or_04 = fields.Boolean(string="CC Book 03 or 04", tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Extended ORM:- CREATE"""
        for vals in vals_list:
            if vals.get('sequence', _('New')) == _('New'):
                vals['sequence'] = self.env['ir.sequence'].with_company(vals.get('company_id')).next_by_code(
                    'workflow.master') or _('New')

        return super().create(vals_list)


    @api.onchange('workflow_ids')
    def onchange_workflow_ids(self):
        for index, record in enumerate(self.workflow_ids, start=1):
            record.sequence = index



