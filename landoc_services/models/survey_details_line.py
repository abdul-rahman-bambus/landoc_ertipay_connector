from odoo import fields, models, api


class SurveyDetailsLine(models.Model):
    _name = 'survey.details.line'
    _description = 'Survey Details Line'

    landoc_services_uid = fields.Many2one('crm.landoc.service')
    ec_village_id = fields.Many2one('res.village', string="Village")
    survey_no = fields.Char(string="Survey No")
    sub_division_no = fields.Char(string="Sub Division No")



class PlotDetailsLine(models.Model):
    _name = 'plot.details.line'
    _description = 'Plot Details Line'

    landoc_services_uid = fields.Many2one('crm.landoc.service')
    ec_plot_no = fields.Char(string="Plot No")


class FlatDetailsLine(models.Model):
    _name = 'flat.details.line'
    _description = 'Flat Details Line'

    landoc_services_uid = fields.Many2one('crm.landoc.service')
    ec_flat_no = fields.Char(string="Flat No")



class HouseDetailsLine(models.Model):
    _name = 'house.details.line'
    _description = 'House Details Line'

    landoc_services_uid = fields.Many2one('crm.landoc.service')
    ec_door_no = fields.Char(string="Door No")
    ec_ward_no = fields.Char(string="Ward No")
    ec_block_no = fields.Char(string="Block No")


class BoundaryDetailsLine(models.Model):
    _name = 'boundary.details.line'
    _description = 'Boundary Details Line'

    landoc_services_uid = fields.Many2one('crm.landoc.service')
    ec_east = fields.Char(string="East")
    ec_west = fields.Char(string="West")
    ec_north = fields.Char(string="North")
    ec_south = fields.Char(string="South")
