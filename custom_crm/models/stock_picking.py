from odoo import fields, models, api



class StockPicking(models.Model):
    _inherit = 'stock.picking'

    lead_id = fields.Many2one(related='sale_id.opportunity_id', store=True, string='Lead')



class StockMove(models.Model):
    _inherit = 'stock.move'

    lead_id = fields.Many2one(related='sale_line_id.order_id.opportunity_id', store=True, string='Lead')


