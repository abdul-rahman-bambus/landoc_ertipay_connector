from odoo import models, fields, api, _
from datetime import date
import logging
_logger = logging.getLogger(__name__)

class CRMLandocService(models.Model):
    _name = "crm.landoc.service"
    _description = "CRM Service"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Service Name", required=True, index=True)

    # From Lead
    lead_id = fields.Many2one(comodel_name="crm.lead", string="Lead")
    service_category_id = fields.Many2one(comodel_name="product.category", domain="[('is_service','=',True)]",
                                          tracking=1, string="Category of Service")
    is_propertychecklist_needed = fields.Boolean(related="service_category_id.is_propertychecklist_needed",
                                                 string="Property Checklist Needed")
    service_id = fields.Many2one(comodel_name="service.type",
                                 domain="[('service_category_id','=',service_category_id)]", tracking=1,
                                 string="Service")
    workflow_master_id = fields.Many2one(comodel_name="workflow.master", string="Workflow Master", tracking=1,
                                         domain="[('category_id', '=', service_category_id)]")
    property_type_id = fields.Many2one(comodel_name="property.type", tracking=1, string="Type of Property")
    is_propertychecklist_needed = fields.Boolean(related="service_category_id.is_propertychecklist_needed",
                                                 string="Property Checklist Needed")
    service_count = fields.Integer(string="Service Count")
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed')], default='draft', tracking=1)

    # EC Fields...
    ec_start_date = fields.Date(string="EC Start Date", tracking=1)
    ec_end_date = fields.Date(string="EC End Date", tracking=1)
    ec_end_date_warning = fields.Char(string="EC End Date Warning")
    survey_no = fields.Char(string="Survey No", tracking=1)
    sub_division_no = fields.Char(string="Sub Division No", tracking=1,)
    whos_name_applied = fields.Char(string="On Whose Name To Be Applied", tracking=1)

    zone_id = fields.Many2one('res.zone', string="Zone", tracking=1)
    district_id = fields.Many2one('res.district', tracking=1, string="DRO")
    sro_id = fields.Many2one('res.sro', tracking=1, string="SRO")

    ec_village_id = fields.Many2one('res.village', tracking=1, string="Village")
    survey_details_line = fields.One2many(comodel_name="survey.details.line", inverse_name="landoc_services_uid")
    # ec_period = fields.Char(string="EC Period")
    ec_plot_no = fields.Char(string="Plot No", tracking=1)
    plot_details_line = fields.One2many(comodel_name="plot.details.line", inverse_name="landoc_services_uid")

    ec_flat_no = fields.Char(string="Flat No", tracking=1)
    flat_details_line = fields.One2many(comodel_name="flat.details.line", inverse_name="landoc_services_uid")

    ec_door_no = fields.Char(string="Door No", tracking=1)
    ec_ward_no = fields.Char(string="Ward No", tracking=1)
    ec_block_no = fields.Char(string="Block No", tracking=1)
    house_details_line = fields.One2many(comodel_name="house.details.line", inverse_name="landoc_services_uid")

    ec_east = fields.Char(string="East", tracking=1)
    ec_west = fields.Char(string="West", tracking=1)
    ec_north = fields.Char(string="North", tracking=1)
    ec_south = fields.Char(string="South", tracking=1)
    boundary_details_line = fields.One2many(comodel_name="boundary.details.line", inverse_name="landoc_services_uid")

    total_extent = fields.Float(string="Total Extent", tracking=1)
    conveyed_extent = fields.Float(string="Conveyed Extent", tracking=1)
    undivided_share = fields.Float(string="Undivided Share", tracking=1)
    build_up_area = fields.Float(string="Build-up Area", tracking=1)

    old_survey_or_sub_div_no = fields.Char(string="Old Survey No./Sub Div No.", tracking=1)
    t_s_no =fields.Char(string="T.S. No.", tracking=1)
    old_door_no = fields.Char(string="Old Door No.", tracking=1)
    name_of_declared_owner = fields.Char(string="Name of Declared Owner", tracking=1)
    father_name = fields.Char(string="Father Name", tracking=1)
    any_other_relevant_info = fields.Char(string="Any Other Relevant Info", tracking=1)
    any_registered_document_no = fields.Char(string="Any Registered Document No.", tracking=1)
    # ec_related_documents = fields.Binary("EC Related Document", attachment=True)  # store pdf
    # ec_related_documents_filename = fields.Char("EC Document Filename")
    is_ec = fields.Boolean(compute="_compute_is_ec")
    extent_sqft_or_area = fields.Selection(selection=[('square_feet', 'Square Feet'), ('acre', 'Acre')], compute='_compute_extent_sqft_or_area', store=True)

    # PWD Info.
    pwd_building_type = fields.Selection([('independent_house', 'Independent House'), ], string="Building Type",
                                         tracking=1)
    pwd_building_age = fields.Char(string="Age of Building (Years)", tracking=1)
    pwd_floor_line = fields.One2many(comodel_name='pwd.floor.line', inverse_name='landoc_service_id')

    # Floor Type.
    pwd_floor_type = fields.Boolean(string="Floor Type")
    pwd_mosaic_color = fields.Boolean(string="Mosaic Color")
    pwd_mosaic_color_text = fields.Char()
    pwd_cuddapah_shahabad_slab = fields.Boolean(string="Cuddapah/Shahabad Slab")
    pwd_cuddapah_shahabad_slab_text = fields.Char()
    pwd_ceramic_tiles = fields.Boolean(string="Ceramic Tiles")
    pwd_ceramic_tiles_text = fields.Char()
    pwd_marble_slabs_1_20_above = fields.Boolean(string="Marble Slabs (1.20 meter or above)")
    pwd_marble_slabs_1_20_above_text = fields.Char()
    pwd_marble_slabs_1_20_below = fields.Boolean(string="Marble Slabs (below 1.20 meter )")
    pwd_marble_slabs_1_20_below_text = fields.Char()
    pwd_dadooing_with_vitrified_tiles = fields.Boolean(string="Dadooing with vitrified tiles")
    pwd_dadooing_with_vitrified_tiles_text = fields.Char()
    pwd_cement_floor = fields.Boolean(string="Cement Floor")
    pwd_cement_floor_text = fields.Char()
    pwd_granite_slabs = fields.Boolean(string="Granite slabs")
    pwd_granite_slabs_text = fields.Char()
    pwd_vitrified_tiles = fields.Boolean(string="Vitrified Tiles")
    pwd_vitrified_tiles_text = fields.Char()
    pwd_marble_tiles = fields.Boolean(string="Marble Tiles")
    pwd_marble_tiles_text = fields.Char()
    pwd_mosaic_gray_color = fields.Boolean(string="Mosaic Gray Color")
    pwd_mosaic_gray_color_text = fields.Char()
    pwd_dadooing_with_mosaic = fields.Boolean(string="Dadooing with mosaic")
    pwd_dadooing_with_mosaic_text = fields.Char()
    pwd_dadooing_with_ceramic_glazed_tiles = fields.Boolean(string="Dadooing with ceramic/glazed tiles")
    pwd_dadooing_with_ceramic_glazed_tiles_text = fields.Char()

    # Building Amenities
    electrical_installations = fields.Boolean(string="Electrical Installations")
    electrical_installations_type = fields.Selection([('general', 'General'), ('detailed', 'Detailed')],
                                                     default='general')
    internal_water_supply = fields.Boolean(string="Internal Water Supply")
    internal_water_supply_type = fields.Selection([('general', 'General'), ('detailed', 'Detailed')], default='general',
                                                  string=' ')
    water_amenities = fields.Boolean(string="Water Amenities")
    municipality_water_tap_connection = fields.Boolean(string="Municipality Water Tap Connection")
    water_number = fields.Char(string="Water Number")
    sanitary_installation = fields.Boolean(string="Sanitary Installation")
    sanitary_installation_type = fields.Selection([('general', 'General'), ('detailed', 'Detailed')], default='general')
    air_condition = fields.Boolean(string="Air Condition")
    electrical_motor = fields.Boolean(string="Electrical Motor")
    gate = fields.Boolean(string="Gate")
    inspection_chamber = fields.Boolean(string="Inspection Chamber")
    latrine = fields.Boolean(string="Latrine")
    open_well = fields.Boolean(string="Open Well")
    other_sanitary_item = fields.Boolean(string="Other Sanitary Item")
    pipeline = fields.Boolean(string="Pipeline")
    over_head_tank = fields.Boolean(string="Over Head Tank")
    lift = fields.Boolean(string="Lift")
    miscellaneous_item = fields.Boolean(string="Miscellaneous Item")
    car_parking = fields.Boolean(string="Car Parking")

    ####################
    # Compute Function
    ####################

    @api.depends('plot_details_line', 'flat_details_line', 'house_details_line', 'boundary_details_line')
    def _compute_extent_sqft_or_area(self):
        for record in self:
            if record.plot_details_line or record.flat_details_line or record.house_details_line:
                record.extent_sqft_or_area = 'square_feet'
            else:
                record.extent_sqft_or_area = 'acre'

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

    @api.onchange('pwd_floor_line')
    def onchange_pwd_floor_line_method(self):
        no_count = 1
        for record in self.pwd_floor_line:
            record.sequence = no_count
            no_count = no_count + 1

    @api.onchange('service_category_id')
    def onchange_service_category_id(self):
        """
        On change service category id, Updating service_id
        """
        self.write({
            'property_type_id': False,
            'workflow_master_id': False,
            'ec_start_date': False,
            'ec_end_date': False,
        })
        if self.service_category_id:
            service_type = self.env['service.type'].search([('service_category_id', '=', self.service_category_id.id)])
            self.service_category_id = service_type.mapped('service_category_id')
            self.service_id = service_type[0] if len(service_type.ids) == 1 else False
            self.service_count = len(service_type)

    @api.onchange('ec_end_date', 'ec_start_date')
    def onchange_ec_end_date(self):
        """
        Onchange for date warning
        """
        current_date = date.today()
        self.ec_end_date_warning = ""
        if self.ec_end_date and self.ec_start_date and current_date:
            if self.ec_end_date == current_date or self.ec_end_date > current_date:
                self.ec_end_date_warning = f"Entered date is a future date"
                self.ec_end_date = False
            if self.ec_end_date and self.ec_start_date and self.ec_end_date < self.ec_start_date:
                self.ec_end_date_warning = f"End date can not be less than start date"
                self.ec_end_date = False


    ################
    # Other Actions
    ################

    def action_set_to_confirm(self):
        active_step = self.lead_id.checklist_tracking_line.filtered(lambda l: l.active_step)
        if len(active_step) == 1:
            active_step.department_status = 'done'
            self.state = 'confirmed'
        if not active_step:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _(f"There is no active step !"),
                }
            }
        if len(active_step) > 1:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _(f"There are multiple active steps !"),
                }
            }

    def action_set_to_draft(self):
        self.state = 'draft'


    ###############
    # EC PROCESS
    ###############

    def action_survey_details(self):
        """
        Action for survey details
        """
        if self.ec_village_id and self.survey_no:
            self.write({'survey_details_line': [(0, 0, {'ec_village_id': self.ec_village_id.id,
                                                        'survey_no': self.survey_no,
                                                        'sub_division_no': self.sub_division_no,
                                                        })]})
            self.ec_village_id = False
            self.survey_no = False
            self.sub_division_no = False

    def action_plot_details(self):
        """
        Action for plot details
        """
        if self.ec_plot_no:
            self.write({'plot_details_line': [(0, 0, {'ec_plot_no': self.ec_plot_no,
                                                        })]})
            self.ec_plot_no = False

    def action_flat_details(self):
        """
        Action for flat details
        """
        if self.ec_flat_no:
            self.write({'flat_details_line': [(0, 0, {'ec_flat_no': self.ec_flat_no,
                                                        })]})
            self.ec_flat_no = False

    def action_house_details(self):
        """
        Action for house details
        """
        if self.ec_door_no or self.ec_ward_no or self.ec_block_no:
            self.write({'house_details_line': [(0, 0, {'ec_door_no': self.ec_door_no,
                                                        'ec_ward_no': self.ec_ward_no,
                                                        'ec_block_no': self.ec_block_no,
                                                        })]})
            self.ec_door_no = False
            self.ec_ward_no = False
            self.ec_block_no = False


    def action_boundary_details(self):
        """
        Action for boundary details
        """
        if self.ec_east or self.ec_west or self.ec_north or self.ec_south:
            self.write({'boundary_details_line': [(0, 0, {'ec_east': self.ec_east,
                                                        'ec_west': self.ec_west,
                                                        'ec_north': self.ec_north,
                                                        'ec_south': self.ec_south,
                                                        })]})
            self.ec_east = False
            self.ec_west = False
            self.ec_north = False
            self.ec_south = False

