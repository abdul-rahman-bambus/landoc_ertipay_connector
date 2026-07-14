from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.tools.mail import is_html_empty


class CrmDepartmentTransfer(models.TransientModel):
    _name = 'crm.department.transfer'
    _description = 'CRM Department Transfer'

    lead_ids = fields.Many2many('crm.lead', string='Leads')
    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True, index=True,
        default=lambda self: self.env.company)
    team_id = fields.Many2one(
        'crm.team', string='Department', check_company=True, index=True)
    feedback = fields.Html(
        'Reason', sanitize=True
    )

    def action_department_transfer(self):
        """Transfer lead and feedback"""
        self.lead_ids.team_id = self.team_id.id
        if not is_html_empty(self.feedback):
            self.lead_ids._track_set_log_message(
                Markup('<div style="margin-bottom: 4px;"><p>%s:</p>%s<br /></div>') % (
                    _('Comment'),
                    self.feedback
                )
            )

        if self.lead_ids.type == 'opportunity':
            crm_kanban_action = self.env['ir.actions.actions']._for_xml_id(
                'crm.crm_lead_action_pipeline')
            crm_kanban_action['target'] = 'main'
            return crm_kanban_action
        else:
            crm_kanban_action = self.env['ir.actions.actions']._for_xml_id(
                'crm.crm_lead_all_leads')
            crm_kanban_action['target'] = 'main'
            return crm_kanban_action
