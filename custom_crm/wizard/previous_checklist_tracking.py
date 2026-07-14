from odoo import api, models, fields


class ChecklistTrackingPrevious(models.TransientModel):
    _name = 'checklist.tracking.previous'
    _description = 'Checklist Tracking Previous'

    choose_step = fields.Selection(selection=[('just_before_step','Just Before Step'), ('jump_previous_checklist_step','Jump Previous Checklist Step')], default="just_before_step", string="Step")
    lead_id = fields.Many2one(comodel_name="crm.lead", readonly=True)
    crm_checklist_tracking_id = fields.Many2one(comodel_name="crm.checklist.tracking", string="Step  ")
    prev_department_id = fields.Many2one(comodel_name="crm.team", string="Previous Department", readonly=True)
    prev_assigned_to_id = fields.Many2one('res.users', string='Previous Assigned To')
    compute_steps = fields.Many2many(comodel_name="crm.checklist.tracking", compute="_compute_steps")
    company_id = fields.Many2one(comodel_name='res.company',index=True)

    ############
    # Compute
    ###########
    @api.depends('lead_id')
    def _compute_steps(self):
        for step in self:
            previous_ids = []
            for checklist in step.lead_id.checklist_tracking_line:
                if checklist.active_step:
                    break
                previous_ids.append(checklist.id)
            step.compute_steps = previous_ids

    ############
    # Action
    ###########
    def action_previous_checklist(self):
        if self.choose_step == 'just_before_step':
            previous_checklist = self.env['crm.checklist.tracking']
            for checklist in self.lead_id.checklist_tracking_line:
                if not checklist.active_step:
                    previous_checklist = checklist
                if checklist.active_step:
                    break
            if previous_checklist:
                for rec in self.lead_id.checklist_tracking_line:
                    rec.active_step = False
            previous_checklist.active_step = True
            previous_checklist.department_status = 'to_do'
            self.prev_department_id = self.lead_id.team_id.id
            self.prev_assigned_to_id = self.lead_id.assigned_to_id.id
            self.sudo().lead_id.team_id = previous_checklist.department_id.id
            self.sudo().lead_id.assigned_to_id = previous_checklist.assigned_to_id.id
            self.sudo().lead_id.landoc_stage = previous_checklist.landoc_stage

        if self.choose_step == 'jump_previous_checklist_step':
            for rec in self.lead_id.checklist_tracking_line:
                rec.active_step = False
            self.crm_checklist_tracking_id.active_step = True
            self.crm_checklist_tracking_id.department_status = 'to_do'
            self.prev_department_id = self.lead_id.team_id.id
            self.prev_assigned_to_id = self.lead_id.assigned_to_id.id
            self.sudo().lead_id.team_id = self.crm_checklist_tracking_id.department_id.id
            self.sudo().lead_id.assigned_to_id = self.crm_checklist_tracking_id.assigned_to_id.id
            self.sudo().lead_id.landoc_stage = self.crm_checklist_tracking_id.landoc_stage

        if self.lead_id.team_id.id != self.prev_department_id.id or self.lead_id.assigned_to_id.id != self.prev_assigned_to_id.id:
            crm_kanban_action = self.env['ir.actions.actions']._for_xml_id('crm.crm_lead_action_pipeline')
            crm_kanban_action['target'] = 'main'
            return crm_kanban_action



