from odoo import fields, models, api, _
from odoo.exceptions import (
    UserError, ValidationError
)
import phonenumbers
from datetime import date
from odoo.tools import date_utils, email_split, groupby, parse_contact_from_email, SQL
from odoo.addons.crm.models import crm_lead
from odoo.addons.crm.models import crm_stage
import logging

_logger = logging.getLogger(__name__)

crm_lead.PARTNER_ADDRESS_FIELDS_TO_SYNC = [
    'street',
    'street2',
    'city',
    'zip',
    'religion_id',
    'city_id',
    'state_id',
    'country_id',
]

crm_stage.AVAILABLE_PRIORITIES = [
    ('0', 'Low'),
    ('1', 'Medium'),
    ('2', 'Normal'),
    ('3', 'High'),
    ('4', 'Very High'),
    ('5', 'Critical'),  # New one
]


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Inherited for changing the string.
    team_id = fields.Many2one(
        'crm.team', string='Department', check_company=True, index=True, tracking=True,
        compute='_compute_team_id', ondelete="set null", readonly=False, store=True, precompute=True)
    assigned_to_id = fields.Many2one('res.users', default=lambda self: self.env.user, string='Assigned To', tracking=True)
    stage_id = fields.Many2one(
        'crm.stage', string='Stage', index=True, tracking=True, readonly=False,
        copy=False, ondelete='restrict')
    expected_revenue = fields.Monetary('Expected Revenue', compute="_compute_expected_revenue", store=True, currency_field='company_currency', tracking=True,
                                       default=0.0)
    is_stage_won = fields.Boolean(string="Is Stage Won", related='stage_id.is_won', store=True)

    # Main fields..
    priority = fields.Selection(
        selection_add=crm_stage.AVAILABLE_PRIORITIES, string='Priority', index=True,
        default=crm_stage.AVAILABLE_PRIORITIES[0][0])

    checklist_input_ids = fields.Many2many(comodel_name='checklist.input', domain="[('lead_id','=',id)]")
    service_booking_ids = fields.Many2many(comodel_name='landoc.service.booking', domain="[('lead_id','=',id)]")
    checklist_counts = fields.Integer(string="Checklist Counts ", compute="_compute_checklist_input_ids")
    service_booking_counts = fields.Integer(string="Booking Counts ", compute="_compute_checklist_input_ids")
    previous_btn_visiblity = fields.Boolean(compute="_compute_checklist_input_ids")
    next_btn_visiblity = fields.Boolean()
    landoc_stage = fields.Char(string="Landoc Stage", readonly=True, tracking=True)
    visible_checklists_btn = fields.Boolean(compute="_compute_visible_checklists_btn")
    checklist_dept_status = fields.Selection(
        [('un_assigned', 'Unassigned'), ('to_do', 'To Do'), ('in_progress', 'In Progress'), ('done', 'Done')],
        default='un_assigned', store=True)
    service_category_id = fields.Many2one(comodel_name="product.category", domain="[('is_service','=',True)]",
                                          tracking=1, string="Category of Service")
    service_id = fields.Many2one(comodel_name="service.type",
                                 domain="[('service_category_id','=',service_category_id)]", tracking=1,
                                 string="Service")
    service_count = fields.Integer(string="Service Count")
    workflow_count = fields.Integer(string="Workflow Count")
    is_propertychecklist_needed = fields.Boolean(related="service_category_id.is_propertychecklist_needed",
                                                 string="Property Checklist Needed")
    is_marriage_category = fields.Boolean(related="service_category_id.is_marriage_category",
                                                 string="Marriage Category")
    service_workflow_ids = fields.Many2many(comodel_name="workflow.master", compute="_compute_service_workflow_ids")
    workflow_master_id = fields.Many2one(comodel_name="workflow.master", string="Workflow Master", tracking=1,
                                         domain="[('category_id', '=', service_category_id)]")
    checklist_tracking_line = fields.One2many(comodel_name='crm.checklist.tracking',
                                              inverse_name='lead_id', string="Checklist")
    sequence = fields.Char(string="Sequence", required=True, copy=False, readonly=False,
                           default=lambda self: _('New'))
    zone_id = fields.Many2one('res.zone', tracking=1, string="Zone")
    religion_id = fields.Many2one('res.religion', string="Religion", tracking=1, compute="_compute_religion_id",
                                  inverse="_inverse_religion_id",
                                  store=True)
    district_id = fields.Many2one('res.district', tracking=1, string="DRO")
    sro_id = fields.Many2one('res.sro', tracking=1, string="SRO")
    sro_zone_ids = fields.Many2many(comodel_name="res.zone", compute='_compute_sro_zone_ids')
    sro_district_ids = fields.Many2many(comodel_name="res.district", compute='_compute_sro_district_ids')
    sro_ids = fields.Many2many(comodel_name="res.sro", compute='_compute_sro_ids')
    village_id = fields.Many2one('res.village', tracking=1, string="Village", domain="[('sro_id', '=', sro_id)]")
    compute_next_step = fields.Char(compute="_compute_next_step")
    name = fields.Char(
        string="Ticket Number",
        required=True, copy=False, readonly=True,
        index='trigram',
        default=lambda self: _('New'))
    property_type_id = fields.Many2one(comodel_name="property.type", tracking=1, string="Type of Property")

    # Service fields..
    is_cc = fields.Boolean(compute="_compute_service_flags")
    is_document_consulting = fields.Boolean(compute="_compute_service_flags")
    is_document_registation = fields.Boolean(compute="_compute_service_flags")
    is_ec = fields.Boolean(compute="_compute_service_flags")
    is_legal_opinion = fields.Boolean(compute="_compute_service_flags")
    is_land_surveying = fields.Boolean(compute="_compute_service_flags")
    is_marriage_registation = fields.Boolean(compute="_compute_service_flags")
    is_revenue_and_local_body = fields.Boolean(compute="_compute_service_flags")
    is_stamp = fields.Boolean(compute="_compute_service_flags")
    is_unregistered_agreement = fields.Boolean(compute="_compute_service_flags")
    is_unregistered_agreement_others = fields.Boolean(compute="_compute_service_flags")

    # Marriage fields..
    date_of_marriage = fields.Date(string="Date of Marriage", default=lambda self: fields.Date.today())
    marriage_place = fields.Char(string="Place of Marriage")
    date_delay_waring = fields.Char(string="Date Delay Warning", compute="_compute_date_delay_waring")
    service_cost = fields.Char(string="Service Cost")
    bride_is_nri = fields.Selection([('yes', 'Yes'),('no', 'No')], string='Bride is NRI')

    groom_is_nri = fields.Selection([('yes', 'Yes'),('no', 'No')], string='Groom is NRI')

    marriage_registration_place_option = fields.Selection([
        ('bride_residence', 'Residence of the Bride'),
        ('groom_residence', 'Residence of the Groom'),
        ('marriage_place', 'Place where the marriage was solemnized')
    ], string='Marriage Registration Place Option')
    marriage_place_option = fields.Selection([('marriage_place', 'Place where the marriage was solemnized')], string='Marriage Registration Place Option')
    visible_marriage_options = fields.Boolean(string='Visible Marriage Options', compute='_compute_visible_marriage_options')
    marriage_service_ids = fields.Many2many(comodel_name="service.type", compute='_compute_marriage_service_ids')

    bride_religion_id = fields.Many2one('res.religion', string="Bride Religion", tracking=1, store=True)
    groom_religion_id = fields.Many2one('res.religion', string="Groom Religion", tracking=1, store=True)

    # EC fields..
    ec_start_date = fields.Date(string="EC Start Date")
    ec_end_date = fields.Date(string="EC End Date")
    ec_no_of_survey = fields.Integer(string="No of Surveys", default=1, tracking=1, required=True)
    is_update_quotation_qty =fields.Boolean(default=False)
    ec_end_date_warning = fields.Char(string="EC End Date Warning")
    ec_additional_year_count = fields.Integer(
        string="Additional Years",
        compute="_compute_year_difference",
    )
    ec_additional_year_amount = fields.Float(
        string="Additional Year Amount",
        compute="_compute_year_difference",
    )
    ec_related_documents = fields.Binary("EC Related Document", attachment=True)  # store pdf
    ec_related_documents_filename = fields.Char("EC Document Filename")
    whos_name_applied = fields.Char(string="On Whose Name To Be Applied")

    # CC fields..
    document_no = fields.Char(string="Document No")
    document_year = fields.Char(string="Year")
    book_no = fields.Selection([('book_1', 'Book 1'), ('book_3/4', 'Book 3/4')], string="Book No")
    cc_book_03_or_04 = fields.Boolean(related="workflow_master_id.book_03_or_04", string="Book 03 Or 04")

    # Buyer fields..
    no_of_buyer = fields.Integer(string="No of Buyer", tracking=1, default=1)
    buyer_party_type = fields.Selection(
        selection=[('individual', 'Individual'), ('company_firm_trust', 'Company/Firm/Trust'),
                   ('government', 'Government')], tracking=1, default="individual", string="Buyer's Party", )
    buyer_name = fields.Char(string="Name", tracking=1)
    buyer_company_tan_no = fields.Char(string="Company Tan No", tracking=1)
    is_buyer_minor = fields.Boolean(default=False, tracking=1)
    is_buyer_representative = fields.Boolean(default=False, tracking=1)

    # Seller fields..
    no_of_seller = fields.Integer(string="No of Seller", tracking=1, default=1)
    seller_party_type = fields.Selection(
        selection=[('individual', 'Individual'), ('company_firm_trust', 'Company/Firm/Trust'),
                   ('government', 'Government')], default="individual", tracking=1, string="Seller's Party", )
    seller_name = fields.Char(string="Name ", tracking=1)
    seller_company_tan_no = fields.Char(string="Company Tan No ", tracking=1)
    is_seller_minor = fields.Boolean(default=False, tracking=1)
    is_seller_representative = fields.Boolean(default=False, tracking=1)

    # Contact fields..
    new_or_existing_customer = fields.Selection(
        selection=[('new_customer', 'New Customer'), ('existing_customer', 'Existing Customer')], tracking=1,
        copy=False, default="new_customer", index=True)
    is_address_required = fields.Selection(
        selection=[('required', 'Required'), ('not_required', 'Not Required')],
        copy=False, default="required", index=True)
    show_address = fields.Boolean(default=False)
    city_id = fields.Many2one("res.city", string="City ", compute='_compute_partner_address_values', readonly=False,
                              tracking=1,
                              store=True)
    city = fields.Char(string='City', related="city_id.name", readonly=True)
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True, tracking=1,
                                  string="Currency .")  # currency of amount currency

    # smart button fields..
    total_invoiced = fields.Monetary(compute='_invoice_total', string="Total Invoiced",
                                     groups='account.group_account_invoice,account.group_account_readonly')
    amount_due_warning = fields.Char(string="Amount Due Warning", compute='_invoice_total', readonly=True,)
    total_expenses = fields.Monetary(string="Checklist Counts", compute='_expenses_total')
    service_process_total = fields.Integer(string="Service Processes Counts", compute='_service_process_total')
    total_vendor_bills = fields.Monetary(string="Vendor Bills", compute='_vendor_bills_total')
    invoice_ids = fields.One2many('account.move', 'lead_id', string='Invoices')
    expense_ids = fields.One2many('hr.expense', 'lead_id', string='Expenses')

    # Timer fields..
    timer_start = fields.Datetime()
    timer_pause = fields.Datetime()
    is_timer_running = fields.Boolean()
    remaining_hours = fields.Float("Remaining Hours", compute="compute_remaining_hours", readonly=True)
    display_timer_start_primary = fields.Boolean(compute='_compute_display_timer_buttons')
    display_timer_stop = fields.Boolean(compute='_compute_display_timer_buttons')
    display_timer_pause = fields.Boolean(compute='_compute_display_timer_buttons')
    display_timer_resume = fields.Boolean(compute='_compute_display_timer_buttons')

    # Account Analytic fields..
    analytic_account_id = fields.Many2one(comodel_name='account.analytic.account', readonly=True)

    # Stock fields..
    lot_ids = fields.Many2many('stock.lot', compute='_compute_lots')

    ################
    # Compute
    ################

    @api.depends('is_marriage_category', 'date_of_marriage')
    def _compute_visible_marriage_options(self):
        for lead in self:
            if (
                    lead.is_marriage_category
                    and lead.date_of_marriage
                    and lead.date_of_marriage > date(2020, 9, 15)
            ):
                lead.visible_marriage_options = True
            else:
                lead.visible_marriage_options = False

    @api.onchange('date_of_marriage', 'bride_religion_id', 'groom_religion_id')
    def _onchange_date_of_marriage(self):
        if self.is_marriage_category:
            self.service_id = False


    @api.depends('date_of_marriage', 'bride_religion_id', 'groom_religion_id')
    def _compute_marriage_service_ids(self):
        service_ids = self.env['service.type'].search([
            ('service_type', '=', 'marriage_registration')
        ])

        services = {
            religion: service_ids.filtered(lambda s: s.religion == religion)
            for religion in ['special', 'christian', 'muslim', 'hindu', 'tamilnadu']
        }

        cutoff_date = date(2009, 11, 23)

        for lead in self:
            bride = lead.bride_religion_id.code
            groom = lead.groom_religion_id.code

            marriage_type = 'other'
            if bride == groom:
                marriage_type = bride

            lead.marriage_service_ids = False

            if marriage_type == 'christian':
                lead.marriage_service_ids = services['christian']
                continue

            if marriage_type == 'other':
                lead.marriage_service_ids = services['special']
                continue

            if marriage_type == 'muslim':
                if lead.date_of_marriage and lead.date_of_marriage > cutoff_date:
                    lead.marriage_service_ids = services['muslim']
                else:
                    lead.marriage_service_ids = services['special']
                continue

            if marriage_type == 'hindu':
                if lead.date_of_marriage and lead.date_of_marriage > cutoff_date:
                    lead.marriage_service_ids = (
                            services['hindu'] | services['tamilnadu']
                    )
                else:
                    lead.marriage_service_ids = services['hindu']


    @api.depends('user_id')
    def _compute_team_id(self):
        """ When changing the user, also set a team_id or restrict team id
        to the ones user_id is member of. """
        for lead in self:
            lead.team_id = lead.user_id.default_department_id

    def _compute_lots(self):
        """
        Compute lots
        """
        StockMove = self.env['stock.move']

        moves = StockMove.search([
            ('lead_id', 'in', self.ids),
            ('picking_id.state', '=', 'done'),
        ])

        move_map = {}

        for move in moves:
            move_map.setdefault(move.lead_id.id, self.env['stock.lot'])
            move_map[move.lead_id.id] |= move.lot_ids


        for rec in self:
            rec.lot_ids = move_map.get(rec.id, self.env['stock.lot'])

    def _service_process_total(self):
        """
        Compute total service process
        """
        for lead in self:
            lead.service_process_total = self.env['crm.landoc.service'].search_count([('lead_id', '=', self.id)])

    @api.depends('ec_start_date', 'ec_end_date')
    def _compute_year_difference(self):
        """
        Compute year difference
        """
        for rec in self:
            if rec.ec_start_date and rec.ec_end_date and rec.ec_end_date >= rec.ec_start_date:
                total_years = abs((rec.ec_end_date.year - rec.ec_start_date.year) - 1)

                rec.ec_additional_year_count = total_years
                landoc_fees = self.env['landoc.fees'].search([('service_id', '=', rec.service_id.id)], limit=1)
                vendor_line = landoc_fees.vendor_fees_line.filtered(
                    lambda l: l.ec_vendor_fee_category == 'search_fee_additional_year')[:1]
                rate_per_year = vendor_line.rate
                rec.ec_additional_year_amount = total_years * rate_per_year
            else:
                rec.ec_additional_year_count = 0
                rec.ec_additional_year_amount = 0

    @api.depends('timer_start', 'timer_pause')
    def _compute_display_timer_buttons(self):
        """
        Compute display timer buttons
        """
        for record in self:
            current_checklist = record.checklist_tracking_line.filtered(lambda l: l.active_step)
            start_p, stop, pause, resume = True, True, True, True
            if current_checklist.timer_start:
                start_p = False
                stop = True
            if current_checklist.timer_pause:
                pause = False
            else:
                resume = False
            if not current_checklist.timer_start:
                stop = False
                pause = False

            record.update({
                'display_timer_start_primary': start_p,
                'display_timer_stop': stop,
                'display_timer_pause': pause,
                'display_timer_resume': resume,
            })

    @api.depends('timer_start', 'timer_pause')
    def compute_remaining_hours(self):
        """
        compute remaining hours
        """
        for record in self:
            checklist_remaining_hours = record.checklist_tracking_line.filtered(lambda l: l.active_step).remaining_hours
            if checklist_remaining_hours:
                record.remaining_hours = checklist_remaining_hours
            else:
                record.remaining_hours = False

    @api.depends('service_id')
    def _compute_service_flags(self):
        """
        Compute all service type boolean flags
        """
        for record in self:
            service_type = record.service_id.service_type if record.service_id else False

            record.is_cc = service_type == 'certified_copy'
            record.is_document_consulting = service_type == 'document_consulting'
            record.is_document_registation = service_type == 'document_registration'
            record.is_ec = service_type == 'encumbrance_certificate'
            record.is_legal_opinion = service_type == 'legal_opinion'
            record.is_land_surveying = service_type == 'land_surveying'
            record.is_marriage_registation = service_type == 'marriage_registration'
            record.is_revenue_and_local_body = service_type == 'revenue_and_local_body_department_works'
            record.is_stamp = service_type == 'stamp_paper'
            record.is_unregistered_agreement = service_type == 'unregistered_agreement'
            record.is_unregistered_agreement_others = service_type == 'unregistered_agreement_others'

    @api.depends('service_category_id')
    def _compute_sro_zone_ids(self):
        """Compute the value of the field sro_zone_ids."""
        for record in self:
            company_ids = self.env.user.company_ids
            company_zone = company_ids.mapped('zone_ids')
            total_zone = False
            for company in company_ids:
                if not company.zone_ids:
                    total_zone = True
                    break
            if company_zone:
                record.sro_zone_ids = company_zone.ids
            if total_zone:
                record.sro_zone_ids = self.env['res.zone'].search([])

    @api.depends('zone_id')
    def _compute_sro_district_ids(self):
        """Compute the value of the field sro_district_ids."""
        for record in self:
            total_zone = []
            company_ids = self.env.user.company_ids
            company_sro_ids = company_ids.mapped('sro_ids')
            for company in company_ids:
                if not company.sro_ids and not company.zone_ids:
                    total_zone += self.env['res.district'].search([]).ids  # ('zone_id', 'in', company.zone_ids.ids)
                if not company.sro_ids and company.zone_ids:
                    total_zone += self.env['res.district'].search([('zone_id', 'in', company.zone_ids.ids)]).ids
            record.sro_district_ids = total_zone + company_sro_ids.mapped('district_id').ids

    @api.depends('district_id')
    def _compute_sro_ids(self):
        """Compute the value of the field sro_ids."""
        for record in self:
            total_zone = []
            company_ids = self.env.user.company_ids
            company_sro_ids = company_ids.mapped('sro_ids')
            for company in company_ids:
                if not company.sro_ids:
                    total_zone += self.env['res.sro'].search([]).ids
            record.sro_ids = total_zone + company_sro_ids.ids

    @api.depends('order_ids.amount_total')
    def _compute_expected_revenue(self):
        for lead in self:
            lead.expected_revenue = sum(lead.order_ids.mapped('amount_total'))

    @api.depends('invoice_ids')
    def _invoice_total(self):
        """
        compute the total invoice amount.
        """
        for lead in self:
            lead_invoices = self.env['account.move'].search(
                [('lead_id', '=', lead.id), ('move_type', '=', 'out_invoice')])
            total_due = sum(lead_invoices.mapped('amount_residual'))
            lead.amount_due_warning = f'Amount Due: {total_due}' if total_due else False
            lead.color = 1 if total_due else 0
            lead.total_invoiced = sum(lead_invoices.mapped('amount_total'))

    @api.depends('invoice_ids')
    def _vendor_bills_total(self):
        """
        compute the total vendor bills amount.
        """
        for lead in self:
            lead_invoices = self.env['account.move'].search(
                [('lead_id', '=', lead.id), ('move_type', '=', 'in_invoice')])
            lead.total_vendor_bills = sum(lead_invoices.mapped('amount_total'))

    @api.depends('expense_ids')
    def _expenses_total(self):
        """
        compute the total expenses amount.
        """
        for lead in self:
            lead_expenses = self.env['hr.expense'].search([('lead_id', '=', lead.id)])
            lead.total_expenses = sum(lead_expenses.mapped('total_amount'))

    def _get_company_currency(self):
        """
        compute the company currency.
        """
        for partner in self:
            if partner.company_id:
                partner.currency_id = partner.sudo().company_id.currency_id
            else:
                partner.currency_id = self.env.company.currency_id

    @api.depends('checklist_tracking_line')
    def _compute_next_step(self):
        """
        compute the next step from checklist stage.
        """
        for step in self:
            next_step = ""
            dept_status = "un_assigned"
            for checklist in step.checklist_tracking_line:
                if checklist.active_step:
                    next_step = checklist.landoc_stage
                    dept_status = checklist.department_status
            step.compute_next_step = next_step
            step.checklist_dept_status = dept_status if dept_status else "un_assigned"

    @api.depends('service_category_id')
    def _compute_service_workflow_ids(self):
        for workflow in self:
            """
            compute the service workflow ids.
            """
            # sub_service = self.env['product.category'].search([('parent_id','=',workflow.service_id.id)])
            # workflows_ids = self.env['workflow.master'].search([('category_id','in', sub_service.ids if sub_service else workflow.service_id.id)])
            workflow.service_workflow_ids = []  # workflows_ids.ids

    @api.depends('checklist_input_ids', 'checklist_tracking_line', 'service_booking_ids')
    def _compute_checklist_input_ids(self):
        """Compute checklists counts and previous_btn_visiblity"""
        for rec in self:
            # Checklists counts
            rec.checklist_counts = len(rec.checklist_input_ids)

            # Service booking counts
            rec.service_booking_counts = len(self.env['landoc.service.booking'].search([('lead_id','=',rec.id)]))

            # # Next Button
            # incompelete_steps = self.checklist_tracking_line.filtered(lambda l: l.department_status != 'done')
            # rec.next_btn_visiblity = False if incompelete_steps else True

            # Previous Button
            rec.previous_btn_visiblity = True
            if not rec.checklist_tracking_line or len(rec.checklist_tracking_line) == 1:
                rec.previous_btn_visiblity = False
            elif rec.checklist_tracking_line:
                previous_ids = []
                for checklist in rec.checklist_tracking_line:
                    previous_ids.append(checklist.id)
                    if checklist.active_step:
                        break
                if len(previous_ids) == 1:
                    rec.previous_btn_visiblity = False
            else:
                rec.previous_btn_visiblity = True

    @api.depends('service_category_id', 'service_id', 'workflow_master_id')
    def _compute_visible_checklists_btn(self):
        for rec in self:
            rec.visible_checklists_btn = True
            if rec.is_ec or (rec.is_cc and not rec.cc_book_03_or_04):
                rec.visible_checklists_btn = False

    @api.depends('partner_id')
    def _compute_religion_id(self):
        """ compute the new values when partner_id has changed """
        for lead in self:
            if not lead.religion_id or lead.partner_id.religion_id:
                lead.religion_id = lead.partner_id.religion_id.id

    def _inverse_religion_id(self):
        """ Update partner_id.religion_id when religion_id is changed on lead """
        for lead in self:
            if lead.partner_id:
                lead.partner_id.religion_id = lead.religion_id

    @api.depends('date_of_marriage')
    def _compute_date_delay_waring(self):
        """
        Compute date of marriage for warnings and  other functions.
        """
        current_date = date.today()
        self.date_delay_waring = ""
        if self.date_of_marriage and self.date_of_marriage < current_date:
            delta = abs(self.date_of_marriage - current_date)
            if delta.days > 150:
                self.date_delay_waring = f"{delta.days} days ago, will charge {self.service_id.fees_above_one_hundred_fifty}"
            elif delta.days > 90:
                self.date_delay_waring = f"{delta.days} days ago, will charge {self.service_id.fees_above_ninety}"

    ################
    # Onchange
    ################

    @api.onchange('ec_no_of_survey')
    def onchange_ec_no_of_survey_method(self):
        """
        Onchange field: is_update_quotation_qty handle Update Quotation button visibility.
        """
        if self.is_ec and self.ec_no_of_survey and self.type == 'opportunity':
            self.is_update_quotation_qty = True


    @api.onchange('ec_end_date', 'ec_start_date')
    def onchange_ec_end_date(self):
        """
        Onchange for EC WF automation and date warnings
        """
        # Workflow Automation for EC
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

    @api.onchange('checklist_tracking_line')
    def onchange_checklist_tracking_line(self):
        """
        Onchange for checklist tracking line
        """
        count = 1
        for line in self.checklist_tracking_line:
            line.sequence = count
            count += 1
        active_step = self.checklist_tracking_line.filtered(lambda l: l.active_step)
        if self.checklist_tracking_line and len(active_step) == 0:
            raise UserError(_("One step should be active."))
        if self.checklist_tracking_line and len(active_step) > 1:
            raise UserError(_("Only one step can be active at a time."))
        if active_step and active_step.landoc_stage != self.landoc_stage:
            self.landoc_stage = active_step.landoc_stage
        if active_step and active_step.department_id.id != self.team_id.id:
            self.team_id = active_step.department_id.id
        if active_step and active_step.assigned_to_id.id != self.assigned_to_id.id:
            self.assigned_to_id = active_step.assigned_to_id.id


    @api.onchange('stage_id')
    def onchange_stage_id(self):
        """
        Onchange Method for stage for preventing users to set won if customer has amount due.
        """
        if self.stage_id.is_won:
            lead_invoices = self.env['account.move'].search(
                [('lead_id', '=', self._origin.id), ('move_type', '=', 'out_invoice')])
            total_due = sum(lead_invoices.mapped('amount_residual'))
            if total_due:
                raise UserError(_(f"The customer has an amount due: {total_due}"))


    @api.onchange('zone_id')
    def onchange_zone_id(self):
        self.write({
            'district_id': False,
            'sro_id': False,
            'village_id': False,
        })

    @api.onchange('district_id')
    def onchange_district_id(self):
        self.write({
            'sro_id': False,
            'village_id': False,
        })

    @api.onchange('sro_id')
    def onchange_sro_id(self):
        self.write({
            'village_id': False,
        })

    @api.onchange('service_category_id')
    def onchange_service_category_id(self):
        """
        Onchange for service category id
        """
        self.write({
            'property_type_id': False,
            'workflow_master_id': False,
            'date_of_marriage': fields.Date.today(),
            'date_delay_waring': False,
            'ec_start_date': False,
            'ec_end_date': False,
            'service_count': False,
            'workflow_count': False,
            'whos_name_applied': False,
            'document_no': False,
            'document_year': False,
            'book_no': False,
        })
        if self.service_category_id:
            # Setting service count if there is only one service.
            service_type = self.env['service.type'].search([('service_category_id', '=', self.service_category_id.id)])
            self.service_id = service_type[0] if len(service_type.ids) == 1 else False
            self.service_count = len(service_type)

            # Setting workflow count if there is only one workflow.
            workflow_master = self.env['workflow.master'].search([('category_id', '=', self.service_category_id.id)])
            self.workflow_master_id = workflow_master[0] if len(workflow_master.ids) == 1 else False
            self.workflow_count = len(workflow_master)

    @api.onchange('new_or_existing_customer')
    def onchange_new_or_existing_customer(self):
        """
        Onchange for new or existing customer
        """
        self.write({
            'contact_name': False,
            'title': False,
            'partner_id': False,
            'street': False,
            'street2': False,
            'city': False,
            'state_id': False,
            'city_id': False,
            'zip': False,
            'country_id': False,
            'mobile': False,
            'phone': False,
            'religion_id': False,
        })

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Onchange for partner id
        """
        self.write({
            'street': self.partner_id.street,
            'street2': self.partner_id.street2,
            'city': self.partner_id.city,
            'state_id': self.partner_id.state_id.id,
            'city_id': self.partner_id.city_id.id,
            'zip': self.partner_id.zip,
            'country_id': self.partner_id.country_id.id,
            'mobile': self.partner_id.mobile,
            'phone': self.partner_id.phone,
            'religion_id': self.partner_id.religion_id.id,
        })

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id and self.country_id != self.state_id.country_id:
            self.city_id = False
            self.state_id = False

    @api.onchange('state_id')
    def _onchange_state(self):
        if self.state_id.country_id and self.country_id != self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id.state_id and self.city_id.state_id != self.state_id:
            self.state_id = self.city_id.state_id
            self.country_id = self.city_id.country_id

    ############
    # ORM
    ############
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                vals['name'] = self.env['ir.sequence'].with_company(self.company_id).next_by_code(
                    'crm.lead') or _('New')

        return super().create(vals_list)

    @api.model
    def default_get(self, default_fields):
        """
        Set values before creating records
        """
        defaults = super().default_get(default_fields)
        defaults.update({'team_id': self.env.user.default_department_id.id,
                         'assigned_to_id': self.env.user.id,
                         })
        return defaults

    #######################
    # Other Functionality
    #######################

    def _prepare_address_values_from_partner(self, partner):
        # Sync all address fields from partner, or none, to avoid mixing them.
        if any(partner[f] for f in crm_lead.PARTNER_ADDRESS_FIELDS_TO_SYNC):
            values = {f: partner[f] for f in crm_lead.PARTNER_ADDRESS_FIELDS_TO_SYNC}
        else:
            values = {f: self[f] for f in crm_lead.PARTNER_ADDRESS_FIELDS_TO_SYNC}
        return values

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set an user as responsible. We prefer that
        # assignment is done automatically (scoring) or manually. Otherwise it
        # would always be root (gateway user). It also allows to exclude portal
        # and public users.
        self = self.with_context(default_user_id=False)

        if custom_values is None:
            custom_values = {}
        defaults = {
            'name': msg_dict.get('subject') or _("No Subject"),
            'email_from': msg_dict.get('from'),
            'partner_id': msg_dict.get('author_id', False),
        }
        if msg_dict.get('priority') in dict(crm_stage.AVAILABLE_PRIORITIES):
            defaults['priority'] = msg_dict.get('priority')
        defaults.update(custom_values)

        return super(CrmLead, self).message_new(msg_dict, custom_values=defaults)

    def _merge_get_fields_address(self):
        """The address fields are propagated as a whole.

        The address is taken from the lead with the most non-empty address field
        (sorted by highest rank if multiple lead have the same amount of non-empty
        fields).
        """
        source_lead = max(self, key=lambda lead: len(list(
            lead[field] for field in crm_lead.PARTNER_ADDRESS_FIELDS_TO_SYNC
            if lead[field]
        )))
        return {fname: source_lead[fname] for fname in crm_lead.PARTNER_ADDRESS_FIELDS_TO_SYNC}

    def _merge_get_fields(self):
        return (
                crm_lead.CRM_LEAD_FIELDS_TO_MERGE
                + list(self._merge_get_fields_specific().keys())
                + crm_lead.PARTNER_ADDRESS_FIELDS_TO_SYNC
        )

    def _prepare_customer_values(self, partner_name, is_company=False, parent_id=False):
        res = super()._prepare_customer_values(partner_name, is_company, parent_id)
        res.update({
            'religion_id': self.religion_id.id,
            'city_id': self.city_id.id,
            'is_company': False,
        })
        return res

    def _prepare_opportunity_quotation_context(self):
        result = super()._prepare_opportunity_quotation_context()
        order_lines = []
        landoc_fees_obj = self.env['landoc.fees'].search([('service_id', '=', self.service_id.id)])

        # Additional Year Calculation
        vendor_rate = 0
        for vendor_fees in landoc_fees_obj.vendor_fees_line:
            vendor_rate += self.ec_additional_year_amount if vendor_fees.ec_vendor_fee_category == 'search_fee_additional_year' else vendor_fees.rate
        for line in landoc_fees_obj.customer_fees_line:
            order_line_dict = {'product_id': line.product_id.id, 'price_unit': line.rate, 'product_uom_qty': 1, 'landoc_fee_line_id':line.id,
                                       'analytic_distribution': {self.analytic_account_id.id: 100}}
            if self.is_ec:
                order_line_dict.update({'price_unit': vendor_rate if line.ec_customer_fee_category == 'govt_fees' else line.rate, 'product_uom_qty': self.ec_no_of_survey if line.ec_customer_fee_category == 'govt_fees' else 1})

            if self.is_marriage_registation:
                current_date = date.today()
                extra_fee = 0
                if self.date_of_marriage and self.date_of_marriage < current_date:
                    delta = abs(self.date_of_marriage - current_date)
                    if delta.days > 150:
                        extra_fee = self.service_id.fees_above_one_hundred_fifty
                    elif delta.days > 90:
                        extra_fee = self.service_id.fees_above_ninety

                order_line_dict.update({'price_unit': line.rate + extra_fee if extra_fee else line.rate,})

            order_lines.append((0, 0, order_line_dict))
            # order_lines.append((0, 0, {'product_id': line.product_id.id, 'price_unit': vendor_rate if line.ec_customer_fee_category == 'govt_fees' else line.rate, 'product_uom_qty': self.ec_no_of_survey if line.ec_customer_fee_category == 'govt_fees' else 1,
            #                            'analytic_distribution': {self.analytic_account_id.id: 100}}))
        result.update({
            'default_order_line': order_lines,
        })
        return result

    def _create_customer(self):
        """ Create a partner from lead data and link it to the lead.

        :return: newly-created partner browse record
        """
        Partner = self.env['res.partner']
        return Partner.create(self._prepare_customer_values(self.contact_name, is_company=False))

    #######################
    # Action Functionality
    #######################

    def action_timer_start(self):
        self.checklist_tracking_line.filtered(lambda l: l.active_step).action_timer_start()

    def action_timer_stop(self):
        self.checklist_tracking_line.filtered(lambda l: l.active_step).action_timer_stop()

    def action_timer_pause(self):
        self.checklist_tracking_line.filtered(lambda l: l.active_step).action_timer_pause()

    def action_timer_resume(self):
        self.checklist_tracking_line.filtered(lambda l: l.active_step).action_timer_resume()

    def action_mob_same_as_phone(self):
        self.write({'phone': self.mobile})

    def action_update_quotation(self):
        """
        Action for updating the quotation Govt. fees qty.
        """
        landoc_fees_obj = self.env['landoc.fees'].search([('service_id', '=', self.service_id.id)])

        # Additional Year Calculation
        vendor_rate = 0
        for vendor_fees in landoc_fees_obj.vendor_fees_line:
            vendor_rate += self.ec_additional_year_amount if vendor_fees.ec_vendor_fee_category == 'search_fee_additional_year' else vendor_fees.rate

        # Fees Updating - Govt fees.
        govt_fee_pdt_id = 0
        for line in landoc_fees_obj.customer_fees_line:
            if line.ec_customer_fee_category == 'govt_fees':
                govt_fee_pdt_id = line.product_id.id
        for order_line in self.sudo().order_ids.order_line:
            if order_line.product_id.id == govt_fee_pdt_id:
                # Triggering Warning for updating order qty if the value less than invoiced.
                if order_line.qty_invoiced > self.ec_no_of_survey:
                    raise ValidationError(f"You cannot update the quotation quantity ({self.ec_no_of_survey}) to less than the invoiced quantity ({int(order_line.qty_invoiced)})")
                order_line.write({'price_unit': vendor_rate, 'product_uom_qty': self.ec_no_of_survey,})
                feedback = f"✅ Quotation updated: government fees set to {self.ec_no_of_survey} as per number of surveys."
                self.message_post(
                    body=feedback,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note'  # Use 'mail.mt_comment' for customer-facing
                )
                self.is_update_quotation_qty = False


    def action_set_won_rainbowman(self):
        """
        Inherited base function.
        Preventing user to set stage won if customer has amount due.
        """
        self.ensure_one()
        lead_invoices = self.env['account.move'].search(
            [('lead_id', '=', self.id), ('move_type', '=', 'out_invoice')])
        total_due = sum(lead_invoices.mapped('amount_residual'))
        if total_due:
            raise UserError(_(f"The customer has an amount due: {total_due}"))
        self.action_set_won()
        message = self._get_rainbowman_message()
        if message:
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': message,
                    'img_url': '/web/image/%s/%s/image_1024' % (self.team_id.user_id._name,
                                                                self.team_id.user_id.id) if self.team_id.user_id.image_1024 else '/web/static/img/smile.svg',
                    'type': 'rainbow_man',
                }
            }
        return True

    def action_view_crm_invoices(self):
        return {
            'name': _('Invoices'),
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'views': [(self.env.ref('custom_crm.view_landoc_out_invoice_tree').id, 'list'), (False, 'form')],
            'type': 'ir.actions.act_window',
            'domain': [('lead_id', '=', self.id), ('move_type', '=', 'out_invoice')],
            'context': {'default_lead_id': self.id, 'default_move_type': 'out_invoice',
                                     'default_partner_id': self.partner_id.id},
        }

    def action_view_crm_expenses(self):
        expense_action = self.env['ir.actions.actions']._for_xml_id('hr_expense.hr_expense_actions_my_all')
        expense_action['domain'] = [('lead_id', '=', self.id)]
        expense_action['context'] = {'default_lead_id': self.id,
                                     'default_payment_mode': 'company_account',
                                     'default_analytic_distribution': {self.analytic_account_id.id: 100.0}}
        return expense_action

    def action_view_process_services(self):
        services = self.mapped('service_process_ids')
        expense_action = self.env['ir.actions.actions']._for_xml_id('landoc_services.action_crm_landoc_service')
        if len(services) > 1:
            expense_action['domain'] = [('lead_id', '=', self.id)]
        elif len(services) == 1:
            form_view = [(self.env.ref('landoc_services.view_crm_landoc_service_form').id, 'form')]
            expense_action['views'] = form_view
            expense_action['res_id'] = services.id
        return expense_action

    def action_view_service_booking(self):
        booking = self.env['landoc.service.booking'].search([('lead_id', '=', self.id)])
        params = self.env['ir.config_parameter'].sudo()
        booking_action = self.env['ir.actions.actions']._for_xml_id('custom_landoc.action_landoc_service_booking')
        booking_action['domain'] = [('lead_id', '=', self.id)]
        booking_action['context'] = {'default_lead_id': self.id,
                                     'default_service_category_id': self.service_category_id.id,
                                     'default_responsible_user_id': int(params.get_param('custom_landoc.responsible_user_id')) or False,
                                     'default_service_id': self.service_id.id, }

        if len(booking) > 1:
            booking_action['domain'] = [('lead_id', '=', self.id)]
            return booking_action
        elif len(booking) == 1:
            form_view = [(self.env.ref('custom_landoc.view_landoc_service_booking_form').id, 'form')]
            booking_action['views'] = form_view
            booking_action['res_id'] = booking.id
        return booking_action


    def action_create_landoc_services(self):
        landoc_service_action = self.env['ir.actions.actions']._for_xml_id(
            'custom_crm.legal_service_process_act_window')
        landoc_service_action['target'] = 'new'
        landoc_service_action['context'] = {'default_lead_id': self.id,
                                            'default_service_category_id': self.service_category_id.id,
                                            'default_service_id': self.service_id.id,
                                            }
        return landoc_service_action

    def action_view_crm_vendor_bills(self):
        move_lines = []
        landoc_fees_obj = self.env['landoc.fees'].search([('service_id', '=', self.service_id.id)])
        if landoc_fees_obj.is_govt_online_payment_required:
            for vendor_line in landoc_fees_obj.vendor_fees_line:
                move_lines.append((0, 0, {'product_id': vendor_line.product_id.id,
                                          'quantity': self.ec_no_of_survey,
                                          'tax_ids': vendor_line.tax_ids.ids,
                                          'price_unit': self.ec_additional_year_amount if vendor_line.ec_vendor_fee_category == 'search_fee_additional_year' else vendor_line.rate,
                                          'analytic_distribution': {self.analytic_account_id.id: 100}}))
        params = self.env['ir.config_parameter'].sudo()
        landoc_vendor_id = int(params.get_param('custom_landoc.landoc_vendor_id')) or False
        if not landoc_vendor_id:
            raise UserError(_("There is no default landoc vendor."))
        vendor_bills = self.env['ir.actions.actions']._for_xml_id('account.action_move_in_invoice')
        vendor_bills['domain'] = [('lead_id', '=', self.id), ('move_type', '=', 'in_invoice')]
        vendor_bills['context'] = {'default_lead_id': self.id, 'default_move_type': 'in_invoice',
                                   'default_partner_id': landoc_vendor_id, 'default_invoice_line_ids': move_lines}
        return vendor_bills

    def action_previous(self):
        """Action Preview."""
        if self.display_timer_start_primary:
            action = self.env['ir.actions.actions']._for_xml_id('custom_crm.action_previous_checklist_tracking_wizard')
            action['context'] = {'default_lead_id': self.id}
            return action

    def action_next(self):
        """Action Next"""
        if self.display_timer_start_primary:
            action = self.env['ir.actions.actions']._for_xml_id('custom_crm.action_checklist_tracking_wizard_wizard')
            action['context'] = {'default_lead_id': self.id}
            return action

    def action_view_checklist(self):
        """Return action for loading checklist input window."""
        action = self.env['ir.actions.actions']._for_xml_id('custom_crm.checklist_input_act_window')
        if len(self.checklist_input_ids.ids) > 1:
            action['domain'] = [('id', 'in', self.checklist_input_ids.ids)]
        elif len(self.checklist_input_ids.ids) == 1:
            form_view = [(self.env.ref('custom_crm.checklist_input_form_view').id, 'form')]
            action['views'] = form_view
            action['res_id'] = self.checklist_input_ids.ids[0]
        return action


    def action_create_checklist(self):
        """Create checklist items based on the selected Sub-Service"""
        check_list_model = self.env['checklist.input']
        checklist_inputs = []
        is_service_checklist = False
        serive_checklist = self.env['checklist.data'].search(
            [('checklist_type', '=', 'service'), ('service_id', '=', self.service_id.id)], limit=1)
        content_checklist = self.env['checklist.data'].search(
            [('checklist_type', '=', 'content'), ('service_id', '=', self.service_id.id)], limit=1)
        content_vals = []
        if content_checklist and self.is_propertychecklist_needed:

            content_list = {'buyer': content_checklist.checklist_data_ids.filtered(lambda l: l.client_type == 'buyer'),
                            'seller': content_checklist.checklist_data_ids.filtered(
                                lambda l: l.client_type == 'seller'),
                            'witness': content_checklist.checklist_data_ids.filtered(
                                lambda l: l.client_type == 'witness'),
                            'minor_guardian': content_checklist.checklist_data_ids.filtered(
                                lambda l: l.client_type == 'minor_guardian'),
                            'representative': content_checklist.checklist_data_ids.filtered(
                                lambda l: l.client_type == 'representative')
                            }

            if content_list.get('buyer'):
                if content_list.get('minor_guardian') and self.is_buyer_minor and self.buyer_party_type == 'individual':
                    for minor_buyer in content_list.get('minor_guardian'):
                        vals = [(0, 0, {
                            # 'name': buyer.name,
                            # 'is_data_required': buyer.is_data_required,
                            'is_buyer_minor': self.is_buyer_minor,
                            'client_type': minor_buyer.client_type,
                            'client_type_name': f"Buyer Guardian",
                            # 'is_attachment_required': buyer.is_attachment_required
                        })]
                        content_vals.extend(vals)
                if content_list.get('representative') and self.is_buyer_representative:
                    representative_buyer = ''
                    if self.buyer_party_type == 'individual':
                        representative_buyer = 'Individual'
                    if self.buyer_party_type == 'company_firm_trust':
                        representative_buyer = 'Company/Firm/Trust'
                    if self.buyer_party_type == 'government':
                        representative_buyer = 'Government'

                    for rep_buyer in content_list.get('representative'):
                        vals = [(0, 0, {
                            # 'name': buyer.name,
                            # 'is_data_required': buyer.is_data_required,
                            'is_buyer_representative': self.is_buyer_representative,
                            'client_type': rep_buyer.client_type,
                            'client_type_name': f"Buyer {representative_buyer} Representative",
                            # 'is_attachment_required': buyer.is_attachment_required
                        })]
                        content_vals.extend(vals)
                for buyer_count in range(self.no_of_buyer):
                    for buyer in content_list.get('buyer'):
                        if self.buyer_party_type == 'individual':
                            vals = [(0, 0, {
                                # 'name': buyer.name,
                                # 'is_data_required': buyer.is_data_required,
                                'client_type': buyer.client_type,
                                'client_type_name': f"Buyer {buyer_count + 1}",
                                'order_sequence': buyer_count + 1,
                                # 'is_attachment_required': buyer.is_attachment_required
                            })]
                            content_vals.extend(vals)

            if content_list.get('seller'):
                if content_list.get(
                        'minor_guardian') and self.is_seller_minor and self.seller_party_type == 'individual':
                    for minor_seller in content_list.get('minor_guardian'):
                        vals = [(0, 0, {
                            # 'name': buyer.name,
                            # 'is_data_required': buyer.is_data_required,
                            'is_seller_minor': self.is_seller_minor,
                            'client_type': minor_seller.client_type,
                            'client_type_name': f"Seller Guardian",
                            # 'is_attachment_required': buyer.is_attachment_required
                        })]
                        content_vals.extend(vals)
                if content_list.get('representative') and self.is_seller_representative:
                    representative_seller = ''
                    if self.seller_party_type == 'individual':
                        representative_seller = 'Individual'
                    if self.seller_party_type == 'company_firm_trust':
                        representative_seller = 'Company/Firm/Trust'
                    if self.seller_party_type == 'government':
                        representative_seller = 'Government'
                    for rep_seller in content_list.get('representative'):
                        vals = [(0, 0, {
                            # 'name': buyer.name,
                            # 'is_data_required': buyer.is_data_required,
                            'is_buyer_representative': self.is_seller_representative,
                            'client_type': rep_seller.client_type,
                            'client_type_name': f"Seller {representative_seller} Representative",
                            # 'is_attachment_required': buyer.is_attachment_required
                        })]
                        content_vals.extend(vals)

                for seller_count in range(self.no_of_seller):
                    for seller in content_list.get('seller'):
                        if self.seller_party_type == 'individual':
                            vals = [(0, 0, {
                                # 'name': buyer.name,
                                # 'is_data_required': buyer.is_data_required,
                                'client_type': seller.client_type,
                                'client_type_name': f"Seller {seller_count + 1}",
                                'order_sequence': seller_count + 1,
                                # 'is_attachment_required': buyer.is_attachment_required
                            })]
                            content_vals.extend(vals)

            if content_list.get('witness'):
                params = self.env['ir.config_parameter'].sudo()
                no_witness = int(params.get_param('custom_landoc.no_witness')) or 2
                for witness_count in range(no_witness):
                    for witness in content_list.get('witness'):
                        vals = [(0, 0, {
                            # 'name': buyer.name,
                            # 'is_data_required': buyer.is_data_required,
                            'client_type': witness.client_type,
                            'client_type_name': f"Witness {witness_count + 1}",
                            'order_sequence': witness_count + 1,
                            # 'is_attachment_required': buyer.is_attachment_required
                        })]
                        content_vals.extend(vals)

        service_vals = []
        if serive_checklist:
            is_service_checklist = True
            for service in serive_checklist.checklist_data_ids:
                vals = [(0, 0, {'name': service.name,
                                'is_data_required': service.is_data_required,
                                'is_attachment_required': service.is_attachment_required})]
                service_vals.extend(vals)

        property_vals = []
        if self.is_propertychecklist_needed and self.property_type_id:
            for property in self.property_type_id.checklist_line:
                vals = [(0, 0, {'name': property.name,
                                'is_data_required': property.is_data_required,
                                # 'client_type': service.client_type,
                                'is_attachment_required': property.is_attachment_required})]
                property_vals.extend(vals)

        if content_vals or property_vals or service_vals:
            checklist_inputs += check_list_model.create(
                {'name': self.name, 'lead_id': self.id, 'is_service_checklist': is_service_checklist,
                 'checklist_line_ids': content_vals,
                 'service_checklist_line': service_vals, 'property_checklist_line': property_vals})
            self.checklist_input_ids = [checklist_input.id for checklist_input in checklist_inputs]
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _(f"Please configure checklist for {self.service_id.name} !"),
                }
            }
