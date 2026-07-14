from odoo import fields, models, api
import logging
_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Guideline Calculation
    building_calculation_pdf = fields.Binary("PDF File", attachment=True, tracking=1)  # store pdf
    building_calculation_pdf_filename = fields.Char("PDF Filename")
    land_area = fields.Float(string="Land Area", tracking=1)
    land_unit = fields.Selection([
        ('sqft', 'Sq. Ft.'),
        ('cent', 'Cent'),
        ('acre', 'Acre'),
    ], string="Unit", tracking=1)
    land_rate = fields.Float(string="Rate (₹ per Unit)", tracking=1)

    total_guideline_value = fields.Float(compute="_compute_total_guideline_value", tracking=1)
    estimated_property_value = fields.Float()
    stamp_duty = fields.Float(related="service_id.stamp_duty")
    is_stamp_percentage = fields.Boolean(related="service_id.is_stamp_percentage")
    registration_fee = fields.Float(related="service_id.registration_fee")
    # is_registration_fee = fields.Boolean(related="service_id.is_registration_fee")
    is_registration_fee_percentage = fields.Boolean(related="service_id.is_registration_fee_percentage")
    government_link = fields.Char("Government Link", compute="_compute_government_link")

    # PWD Info.
    pwd_building_type =  fields.Selection([('independent_house', 'Independent House'),], string="Building Type", tracking=1)
    pwd_building_age = fields.Char(string="Age of Building (Years)", tracking=1)
    pwd_floor_line = fields.One2many(comodel_name='pwd.floor.line', inverse_name='lead_id')

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
    pwd_dadooing_with_mosaic =fields.Boolean(string="Dadooing with mosaic")
    pwd_dadooing_with_mosaic_text = fields.Char()
    pwd_dadooing_with_ceramic_glazed_tiles = fields.Boolean(string="Dadooing with ceramic/glazed tiles")
    pwd_dadooing_with_ceramic_glazed_tiles_text = fields.Char()

    # Building Amenities
    electrical_installations = fields.Boolean(string="Electrical Installations")
    electrical_installations_type = fields.Selection([('general', 'General'), ('detailed', 'Detailed')], default='general')
    internal_water_supply = fields.Boolean(string="Internal Water Supply")
    internal_water_supply_type = fields.Selection([('general', 'General'), ('detailed', 'Detailed')], default='general', string=' ')
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


    ###########
    # Compute
    ###########

    def _compute_government_link(self):
        """
        Compute the government link from landoc settings.
        """
        params = self.env['ir.config_parameter'].sudo()
        for record in self:
            record.government_link = params.get_param('custom_landoc.government_link') or False

    def action_open_government_link(self):
        """
        Open a government link
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.government_link,
            'target': 'new',
        }

    @api.depends('estimated_property_value', 'stamp_duty', 'registration_fee')
    def _compute_total_guideline_value(self):
        """
        Compute the total guideline value from stamp_duty and registration_fee.
        """
        for record in self:
            stamp_duty = (record.estimated_property_value * record.stamp_duty/100) if record.is_stamp_percentage else record.stamp_duty
            registration_fee = (record.estimated_property_value * record.registration_fee/100) if record.is_registration_fee_percentage else record.registration_fee
            record.total_guideline_value = stamp_duty + registration_fee if record.estimated_property_value else 0



    ############
    # Onchange
    ###########

    @api.onchange('pwd_floor_line')
    def onchange_pwd_floor_line_method(self):
        no_count = 1
        for record in self.pwd_floor_line:
            record.sequence = no_count
            no_count = no_count + 1

