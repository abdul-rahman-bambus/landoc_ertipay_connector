from odoo import fields, models, api


class FieldData(models.Model):
    _name = 'field.data'
    _description = 'Field Data'
    _order = 'sequence, id'

    name = fields.Char(string="Description")
    sequence = fields.Integer(string="Sequence", default=10)
    checklist_data_id = fields.Many2one(comodel_name="checklist.data")
    checklist_type = fields.Selection(related="checklist_data_id.checklist_type")
    description_code = fields.Char(string="Description Code", compute="_compute_description_code")
    client_type = fields.Selection(selection=[('buyer', 'Buyer'), ('seller', 'Seller'), ('witness', 'Witness'),
                                              ('minor_guardian', 'Minor/Guardian'), ('representative', 'Representative')], string="Client Type",
                                   copy=False, index=True)
    is_data_required = fields.Boolean(string="Data")
    is_attachment_required = fields.Boolean(string="Attachment")
    company_id = fields.Many2one(comodel_name='res.company', index=True)

    @api.depends('checklist_data_id')
    def _compute_description_code(self):
        for data in self:
            description_code = data.name.replace(" ", "_") if data.name else data.name
            data.description_code = description_code.lower() if description_code else False
