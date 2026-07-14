from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    service_process_ids = fields.One2many(comodel_name='crm.landoc.service', inverse_name='lead_id', string='Service Processes')
    visibility_proceed_service = fields.Boolean(compute='_compute_visibility_proceed_service')

    ############
    # Compute
    ###########

    @api.depends('invoice_ids', 'service_process_ids')
    def _compute_visibility_proceed_service(self):
        """
        Compute visibility proceed service
        """
        for record in self:
            if record.invoice_ids.filtered(lambda l: l.state not in ('draft', 'cancel')):
                record.visibility_proceed_service = True
            else:
                record.visibility_proceed_service = False

