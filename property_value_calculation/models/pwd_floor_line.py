from odoo import fields, models, api

FLOOR_SELECTION = [
    ('ground_floor', 'Ground Floor'),
    ('first_floor', 'First Floor'),
    ('second_floor', 'Second Floor'),
    ('third_floor', 'Third Floor'),
    ('fourth_floor', 'Fourth Floor'),
    ('fifth_floor', 'Fifth Floor'),
    ('sixth_floor', 'Sixth Floor'),
    ('seventh_floor', 'Seventh Floor'),
    ('eighth_floor', 'Eighth Floor'),
    ('ninth_floor', 'Ninth Floor'),
    ('tenth_floor', 'Tenth Floor'),
    ('eleventh_floor', 'Eleventh Floor'),
    ('twelfth_floor', 'Twelfth Floor'),
    ('thirteenth_floor', 'Thirteenth Floor'),
    ('fourteenth_floor', 'Fourteenth Floor'),
    ('fifteenth_floor', 'Fifteenth Floor'),
    ('sixteenth_floor', 'Sixteenth Floor'),
    ('seventeenth_floor', 'Seventeenth Floor'),
    ('eighteenth_floor', 'Eighteenth Floor'),
    ('nineteenth_floor', 'Nineteenth Floor'),
    ('twentieth_floor', 'Twentieth Floor'),
    ('twenty_first_floor', 'Twenty First Floor'),
    ('twenty_second_floor', 'Twenty Second Floor'),
    ('twenty_third_floor', 'Twenty Third Floor'),
    ('twenty_fourth_floor', 'Twenty Fourth Floor'),
    ('twenty_fifth_floor', 'Twenty Fifth Floor'),
    ('twenty_sixth_floor', 'Twenty Sixth Floor'),
    ('twenty_seventh_floor', 'Twenty Seventh Floor'),
    ('twenty_eighth_floor', 'Twenty Eighth Floor'),
    ('twenty_ninth_floor', 'Twenty Ninth Floor'),
    ('thirtieth_floor', 'Thirtieth Floor'),
    ('thirty_first_floor', 'Thirty First Floor'),
    ('thirty_second_floor', 'Thirty Second Floor'),
    ('thirty_third_floor', 'Thirty Third Floor'),
    ('thirty_fourth_floor', 'Thirty Fourth Floor'),
    ('thirty_fifth_floor', 'Thirty Fifth Floor'),
    ('thirty_sixth_floor', 'Thirty Sixth Floor'),
    ('thirty_seventh_floor', 'Thirty Seventh Floor'),
    ('thirty_eighth_floor', 'Thirty Eighth Floor'),
    ('thirty_ninth_floor', 'Thirty Ninth Floor'),
    ('fortieth_floor', 'Fortieth Floor'),
    ('forty_first_floor', 'Forty First Floor'),
    ('forty_second_floor', 'Forty Second Floor'),
    ('forty_third_floor', 'Forty Third Floor'),
    ('forty_fourth_floor', 'Forty Fourth Floor'),
    ('forty_fifth_floor', 'Forty Fifth Floor'),
    ('forty_sixth_floor', 'Forty Sixth Floor'),
    ('forty_seventh_floor', 'Forty Seventh Floor'),
    ('forty_eighth_floor', 'Forty Eighth Floor'),
    ('basement_floor', 'Basement Floor'),
    ('basement_first_floor', 'Basement First Floor'),
    ('basement_second_floor', 'Basement Second Floor'),
    ('basement_third_floor', 'Basement Third Floor'),
    ('basement_fourth_floor', 'Basement Fourth Floor'),
]


class PWDFloorLine(models.Model):
    _name = 'pwd.floor.line'
    _description = 'PWD Floor Line'

    lead_id = fields.Many2one('crm.lead')
    sequence = fields.Char(string="Sequence")

    floor_name = fields.Selection(selection=FLOOR_SELECTION, required=True)
    area_sqft = fields.Float(string="Area Sq.Ft.")
    material_type = fields.Selection(
        selection=[
            ('mud_mortar', 'Mud Mortar'),
            ('mud_mortar_and_partially_rr_masonry', 'Mud Mortar and RR. Masonry'),
            ('cement_mortar', 'Cement Mortar'),
            ('cement_lime_mortar', 'Cement/Lime Mortar'),
            ('partly_cement_lime_partly_mud_mortar', 'Partly Cement/Lime & Partly Mud Mortar'),
        ],
        string="Material Type")
    wood_type = fields.Selection(
        selection=[('country', 'Country'), ('partly_wood_and_partly_steel', 'Partly Wood & Partly Steel'),
                   ('steel_frame', 'Steel Frame'),
                   ('teak', 'Teak'),
                   ('upvc', 'UPVC'),
                   ],
    )
    roof_type = fields.Selection(selection=[
        ('ac_sheet', 'AC Sheet'),
        ('madras_terrace', 'Madras Terrace'),
        ('mangalore_tiles_over_flat_tiles', 'Mangalore Tiles Over Flat Tiles'),
        ('pan_tiles_over_flat_tiles', 'Pan Tiles Over Flat Tiles'),
        ('pan_tiles_without_flat_tiles', 'Pan Tiles Without Flat Tiles'),
        ('plain_mangalore_tiles', 'Plain Mangalore Tiles'),
        ('rcc_slab', 'RCC Slab'),
        ('roof_with_gi_sheet', 'Roof With Gi Sheet'),
    ], string="Roof Type")
