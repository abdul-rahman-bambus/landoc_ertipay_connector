from odoo import api, models, fields, _
from datetime import date


class LegalServiceProcess(models.TransientModel):
    _name = 'legal.service.process'
    _description = 'Legal Service Process'

    service_category_id = fields.Many2one(comodel_name="product.category", domain="[('is_service','=',True)]", string="Category of Service")
    is_propertychecklist_needed = fields.Boolean(related="service_category_id.is_propertychecklist_needed",
                                                 string="Property Checklist Needed")
    service_id = fields.Many2one(comodel_name="service.type",
                                 domain="[('service_category_id','=',service_category_id)]", string="Service")
    workflow_master_id = fields.Many2one(comodel_name="workflow.master", string="Workflow Master")
    lead_id = fields.Many2one(comodel_name="crm.lead", string="Lead")

    # EC Fields...
    ec_start_date = fields.Date(string="EC Start Date")
    ec_end_date = fields.Date(string="EC End Date")
    ec_end_date_warning = fields.Char(string="EC End Date Warning")
    is_ec_apply = fields.Boolean(string="Is EC Applied")
    is_ec = fields.Boolean(compute="_compute_is_ec")

    ####################
    # Compute Function
    ####################

    @api.depends('service_id')
    def _compute_is_ec(self):
        """
        To compute marriage EC boolean
        """
        for record in self:
            if record.service_id.service_type == 'encumbrance_certificate':
                record.is_ec = True
            else:
                record.is_ec = False

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

    ###########
    # Action.
    ###########
    def generate_landoc_service(self):
        crm_landoc_service = self.env['crm.landoc.service']
        service_dict = {
            'name': f"{self.lead_id.name} - {self.lead_id.service_id.name}",
            'service_category_id': self.lead_id.service_category_id.id,
            'property_type_id': self.lead_id.property_type_id.id,
            'workflow_master_id': self.lead_id.workflow_master_id.id,
            'service_id': self.lead_id.service_id.id,
            'zone_id': self.lead_id.zone_id.id,
            'district_id': self.lead_id.district_id.id,
            'sro_id': self.lead_id.sro_id.id,
            'ec_village_id': self.lead_id.village_id.id,
            'ec_start_date': self.lead_id.ec_start_date,
            'ec_end_date': self.lead_id.ec_end_date,
            'survey_no': '-',
            'lead_id': self.lead_id.id,
        }
        if self.is_propertychecklist_needed:
            service_dict.update({'pwd_building_type': self.lead_id.pwd_building_type,
                                 'pwd_building_age': self.lead_id.pwd_building_age,
                                 # pwd_floor_line = fields.One2many(comodel_name='pwd.floor.line', inverse_name='landoc_service_id')

                                 # Floor Type.
                                 'pwd_floor_type': self.lead_id.pwd_floor_type,
                                 'pwd_mosaic_color': self.lead_id.pwd_mosaic_color,
                                 'pwd_mosaic_color_text': self.lead_id.pwd_mosaic_color_text,
                                 'pwd_cuddapah_shahabad_slab': self.lead_id.pwd_cuddapah_shahabad_slab,
                                 'pwd_cuddapah_shahabad_slab_text': self.lead_id.pwd_cuddapah_shahabad_slab_text,
                                 'pwd_ceramic_tiles': self.lead_id.pwd_ceramic_tiles,
                                 'pwd_ceramic_tiles_text': self.lead_id.pwd_ceramic_tiles_text,
                                 'pwd_marble_slabs_1_20_above': self.lead_id.pwd_marble_slabs_1_20_above,
                                 'pwd_marble_slabs_1_20_above_text': self.lead_id.pwd_marble_slabs_1_20_above_text,
                                 'pwd_marble_slabs_1_20_below': self.lead_id.pwd_marble_slabs_1_20_below,
                                 'pwd_marble_slabs_1_20_below_text': self.lead_id.pwd_marble_slabs_1_20_below_text,
                                 'pwd_dadooing_with_vitrified_tiles': self.lead_id.pwd_dadooing_with_vitrified_tiles,
                                 'pwd_dadooing_with_vitrified_tiles_text': self.lead_id.pwd_dadooing_with_vitrified_tiles_text,
                                 'pwd_cement_floor': self.lead_id.pwd_cement_floor,
                                 'pwd_cement_floor_text': self.lead_id.pwd_cement_floor_text,
                                 'pwd_granite_slabs': self.lead_id.pwd_granite_slabs,
                                 'pwd_granite_slabs_text': self.lead_id.pwd_granite_slabs_text,
                                 'pwd_vitrified_tiles': self.lead_id.pwd_vitrified_tiles,
                                 'pwd_vitrified_tiles_text': self.lead_id.pwd_vitrified_tiles_text,
                                 'pwd_marble_tiles': self.lead_id.pwd_marble_tiles,
                                 'pwd_marble_tiles_text': self.lead_id.pwd_marble_tiles_text,
                                 'pwd_mosaic_gray_color': self.lead_id.pwd_mosaic_gray_color,
                                 'pwd_mosaic_gray_color_text': self.lead_id.pwd_mosaic_gray_color_text,
                                 'pwd_dadooing_with_mosaic': self.lead_id.pwd_dadooing_with_mosaic,
                                 'pwd_dadooing_with_mosaic_text': self.lead_id.pwd_dadooing_with_mosaic_text,
                                 'pwd_dadooing_with_ceramic_glazed_tiles': self.lead_id.pwd_dadooing_with_ceramic_glazed_tiles,
                                 'pwd_dadooing_with_ceramic_glazed_tiles_text': self.lead_id.pwd_dadooing_with_ceramic_glazed_tiles_text,

                                 # Building Amenities
                                 'electrical_installations': self.lead_id.electrical_installations,
                                 'electrical_installations_type': self.lead_id.electrical_installations_type,
                                 'internal_water_supply': self.lead_id.internal_water_supply,
                                 'internal_water_supply_type': self.lead_id.internal_water_supply_type,
                                 'water_amenities': self.lead_id.water_amenities,
                                 'municipality_water_tap_connection': self.lead_id.municipality_water_tap_connection,
                                 'water_number': self.lead_id.water_number,
                                 'sanitary_installation': self.lead_id.sanitary_installation,
                                 'sanitary_installation_type': self.lead_id.sanitary_installation_type,
                                 'air_condition': self.lead_id.air_condition,
                                 'electrical_motor': self.lead_id.electrical_motor,
                                 'gate': self.lead_id.gate,
                                 'inspection_chamber': self.lead_id.inspection_chamber,
                                 'latrine': self.lead_id.latrine,
                                 'open_well': self.lead_id.open_well,
                                 'other_sanitary_item': self.lead_id.other_sanitary_item,
                                 'pipeline': self.lead_id.pipeline,
                                 'over_head_tank': self.lead_id.over_head_tank,
                                 'lift': self.lead_id.lift,
                                 'miscellaneous_item': self.lead_id.miscellaneous_item,
                                 'car_parking': self.lead_id.car_parking,
                                 })
        landoc_service_id = crm_landoc_service.create(service_dict)
        for rec in self.lead_id.pwd_floor_line:
            rec.landoc_service_id = landoc_service_id
        if self.is_ec_apply:
            ec_service_obj = self.env['service.type'].search([('service_type', '=', 'encumbrance_certificate')],
                                                             limit=1)
            crm_landoc_service.create({
                'name': f"{self.lead_id.name} - {ec_service_obj.name}",
                'service_category_id': ec_service_obj.service_category_id.id,
                'workflow_master_id': self.workflow_master_id.id,
                'service_id': ec_service_obj.id,
                'zone_id': self.lead_id.zone_id.id,
                'district_id': self.lead_id.district_id.id,
                'sro_id': self.lead_id.sro_id.id,
                'ec_village_id': self.lead_id.village_id.id,
                'ec_start_date': self.ec_start_date,
                'ec_end_date': self.ec_end_date,
                'survey_no': '-',
                'lead_id': self.lead_id.id,
            })
