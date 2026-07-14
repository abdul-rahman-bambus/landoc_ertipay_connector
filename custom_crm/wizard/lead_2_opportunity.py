from odoo import fields, models, api, _
from datetime import date


class Lead2OpportunityPartner(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'

    @api.model
    def _get_new_name_type(self):
        selection = [('convert', 'Convert to opportunity'), ]
        return selection

    name = fields.Selection(
        selection='_get_new_name_type',
        string='Conversion Action', compute=False, default='convert', readonly=False, store=True, compute_sudo=False)

    action_view = fields.Selection([
        ('create', 'Create a new customer'),
        ('exist', 'Link to an existing customer'),
        #('nothing', 'Do not link to a customer')
    ], string='Related Customer ', compute='_compute_action', readonly=False, store=True, compute_sudo=False)
    team_id = fields.Many2one('crm.team', 'Department', related='lead_id.team_id')

    # Service Process fields
    service_category_id = fields.Many2one(comodel_name="product.category", domain="[('is_service','=',True)]", related="lead_id.service_category_id",
                                          string="Category of Service")
    is_propertychecklist_needed = fields.Boolean(related="service_category_id.is_propertychecklist_needed",
                                                 string="Property Checklist Needed")
    service_id = fields.Many2one(comodel_name="service.type",
                                 domain="[('service_category_id','=',service_category_id)]", related="lead_id.service_id", string="Service")
    workflow_master_id = fields.Many2one(comodel_name="workflow.master", string="Workflow Master")

    # EC Fields...
    ec_start_date = fields.Date(string="EC Start Date")
    ec_end_date = fields.Date(string="EC End Date")
    ec_end_date_warning = fields.Char(string="EC End Date Warning")
    is_ec_apply = fields.Boolean(string="Is EC Applied")
    is_ec = fields.Boolean(compute="_compute_service_flags")
    is_document_registation = fields.Boolean(compute="_compute_service_flags")
    service_visibility = fields.Boolean(compute="_compute_service_visibility")

    ####################
    # Compute Function
    ####################

    @api.depends('service_id')
    def _compute_service_flags(self):
        """
        To compute service flags.
        """
        for record in self:
            service_type = record.service_id.service_type if record.service_id else False

            record.is_document_registation = service_type == 'document_registration'
            record.is_ec = service_type == 'encumbrance_certificate'

    @api.depends('service_id')
    def _compute_service_visibility(self):
        for record in self:
            record.service_visibility = True if record.is_ec or record.is_document_registation else False


    @api.depends('lead_id')
    def _compute_action(self):
        for convert in self:
            # partner = convert.lead_id._find_matching_partner()
            if convert.lead_id.new_or_existing_customer == 'existing_customer':
                convert.action = 'exist'
                convert.action_view = 'exist'
            elif convert.lead_id.new_or_existing_customer == 'new_customer':
                convert.action = 'create'
                convert.action_view = 'create'

    #############
    # Onchange.
    #############

    @api.onchange('ec_end_date', 'ec_start_date')
    def onchange_ec_end_date(self):
        # Workflow Automation
        if self.ec_start_date and self.ec_start_date.year < 1975:
            self.workflow_master_id = self.env['workflow.master'].search([('ec_year_applicable', '=', 'before_1975')],
                                                                         limit=1)
        if self.ec_start_date and self.ec_start_date.year >= 1975:
            self.workflow_master_id = self.env['workflow.master'].search([('ec_year_applicable', '=', 'after_1975')],
                                                                         limit=1)

        # EC end date warning
        current_date = date.today()
        self.ec_end_date_warning = ""
        if self.ec_end_date and self.ec_start_date and current_date:
            if self.ec_end_date == current_date or self.ec_end_date > current_date:
                self.ec_end_date_warning = f"Entered date is a future date"
                self.ec_end_date = False
            if self.ec_end_date and self.ec_start_date and self.ec_end_date < self.ec_start_date:
                self.ec_end_date_warning = f"End date can not be less than start date"
                self.ec_end_date = False

    @api.onchange('action_view')
    def action_view_onchange_method(self):
        self.action = self.action_view


    def action_apply(self):
        res = super().action_apply()
        analytic_plan_id = self.env.ref('custom_crm.analytic_landoc_lead')
        analytic = self.env['account.analytic.account'].create({
            'name': self.lead_id.name,
            'partner_id': self.lead_id.partner_id.id,
            'company_id': self.lead_id.company_id.id,
            'plan_id': analytic_plan_id.id,
            'lead_id': self.lead_id.id,
        })
        self.lead_id.analytic_account_id = analytic.id
        service_vals = {'lead_id': self.lead_id.id,
                                            'service_category_id': self.lead_id.service_category_id.id,
                                            'service_id': self.lead_id.service_id.id,
                                            }
        if self.is_ec_apply:
            service_vals.update({'ec_start_date': self.ec_start_date,'ec_end_date': self.ec_end_date, 'is_ec_apply':self.is_ec_apply, 'workflow_master_id': self.workflow_master_id.id})
        if self.is_ec or self.lead_id.is_document_registation:
            service_obj = self.env['legal.service.process'].sudo().create(service_vals)
            service_obj.generate_landoc_service()
        try:
            self.lead_id.sudo().action_create_checklist()
        except Exception as e:
            _logger.exception(e)

        return res
