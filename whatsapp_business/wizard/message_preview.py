from odoo import api, fields, models
from bs4 import BeautifulSoup
import html
import re

class MessagePreview(models.TransientModel):
    _name = 'message.preview'
    _description = 'Preview template'

    @api.model
    def _selection_target_model(self):
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([])]

    template_id = fields.Many2one(comodel_name="template.whatsapp", string="Templates")
    preview_whatsapp = fields.Html(compute="_compute_preview_message", string="Message Preview")
    test_record = fields.Reference(
        string='Record',
        compute='_compute_resource_ref',
        compute_sudo=False, readonly=False,
        selection='_selection_target_model',
        store=True
    )
    no_record = fields.Boolean('No Record', compute='_compute_no_record')

    ##############################
    # Compute functions
    ###############################

    @api.depends('template_id')
    def _compute_no_record(self):
        for preview, preview_sudo in zip(self, self.sudo()):
            model_id = preview_sudo.template_id.model_id
            preview.no_record = not model_id or not self.env[model_id.model].search_count([])

    @api.depends('template_id')
    def _compute_resource_ref(self):
        for preview in self:
            if preview.template_id:
                mail_template = preview.template_id.sudo()
                model = mail_template.model_id.model
                res = self.env[model].search([], limit=1)
                preview.test_record = f'{model},{res.id}' if res else False
            else:
                preview.test_record = False

    @api.depends('template_id', 'test_record')
    def _compute_preview_message(self):
        for record in self:
            if record.template_id:
                record.preview_whatsapp = record.template_id._get_preview_message(self.test_record)
            else:
                record.preview_whatsapp = None

