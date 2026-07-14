from odoo import api, models, fields, _
from markupsafe import Markup


class ChecklistTrackingWizard(models.TransientModel):
    _name = 'checklist.tracking.wizard'
    _description = 'Checklist Tracking Wizard'

    comments = fields.Text()
    lead_id = fields.Many2one(comodel_name="crm.lead", readonly=True)
    workflow_master_id = fields.Many2one(comodel_name="workflow.master", string="Workflow Master")
    workflow_line_id = fields.Many2one(comodel_name="workflow.line")
    crm_checklist_tracking_id = fields.Many2one(comodel_name="crm.checklist.tracking", string="Step")
    choose_step = fields.Selection(selection=[('next_worklow_step','Next Workflow Step'), ('jump_next_checklist_step','Jump Next Checklist Step')], default="next_worklow_step", string="Step ")
    attachment_file = fields.Binary()
    # attachment_ids = fields.One2many(
    #     'ir.attachment',
    #     'res_id',
    #     domain=lambda self: [('res_model', '=', self._name)],
    #     string="Attachments"
    # )
    file_name = fields.Char()
    landoc_stage = fields.Char(string="Landoc Stage", readonly=True,)
    department_id = fields.Many2one(comodel_name="crm.team", string="Department", readonly=True,)
    assigned_to_id = fields.Many2one('res.users', string='Assigned To')
    prev_department_id = fields.Many2one(comodel_name="crm.team", string="Previous Department", readonly=True)
    prev_assigned_to_id = fields.Many2one('res.users', string='Previous Assigned To')
    dept_members_ids = fields.Many2many('res.users', string='Members', compute='_compute_department_members_ids')
    stage_id = fields.Many2one(comodel_name="crm.stage", string="Stage", readonly=True,)
    compute_steps = fields.Many2many(comodel_name="crm.checklist.tracking", compute="_compute_steps")
    is_next_workflow = fields.Boolean(default=False)
    company_id = fields.Many2one(comodel_name='res.company',index=True)

    ################
    # Compute
    ################

    @api.depends('lead_id')
    def _compute_department_members_ids(self):
        for member in self:
            if member.department_id:
                members_list = member.department_id.member_ids.ids
                if member.department_id.user_id:
                    members_list.append(member.department_id.user_id.id)
                member.dept_members_ids = members_list
            else:
                member.dept_members_ids = []

    @api.depends('lead_id')
    def _compute_steps(self):
        for step in self:
            check_point = False
            next_ids = []
            for checklist in step.lead_id.checklist_tracking_line:
                if check_point:
                    next_ids.append(checklist.id)
                if checklist.active_step:
                    check_point = True
            step.compute_steps = next_ids

    @api.model
    def default_get(self, default_fields):
        defaults = super().default_get(default_fields)
        lead_id = self.env['crm.lead'].browse(defaults['lead_id'])
        if lead_id:
            defaults.update({'workflow_master_id': lead_id.workflow_master_id.id})
        return defaults

    def _next_workflows(self,lead_id):
        last_workflow_line = []
        for checklist_track in lead_id.checklist_tracking_line:
            last_workflow_line.append(checklist_track.workflow_line_id.id)
        for workflow in lead_id.workflow_master_id.workflow_ids:
            if not lead_id.checklist_tracking_line:
                track_line = []
                dept_id = False
                for sub_checklists in lead_id.workflow_master_id.workflow_ids:
                    if workflow.id == sub_checklists.id:
                        # track_line.append(sub_checklists.id)
                        dept_id = workflow.department_id.id
                    if dept_id == sub_checklists.department_id.id:
                        track_line.append(sub_checklists)
                    if dept_id != sub_checklists.department_id.id:
                        break
                return track_line
            if workflow.id not in last_workflow_line:
                track_line = []
                dept_id = False
                for sub_checklists in lead_id.workflow_master_id.workflow_ids:
                    if workflow.id == sub_checklists.id:
                        dept_id = workflow.department_id.id
                    if dept_id and dept_id == sub_checklists.department_id.id:
                        track_line.append(sub_checklists)
                    if dept_id and dept_id != sub_checklists.department_id.id:
                        break
                return track_line

    ############
    # Onchange
    ###########
    @api.onchange('choose_step')
    def onchange_choose_step(self):
        if self.choose_step == 'next_worklow_step':
            val_list = {}
            defaults = {}
            last_workflow_line = []
            for checklist_track in self.lead_id.checklist_tracking_line:
                last_workflow_line.append(checklist_track.workflow_line_id.id)
            for workflow in self.lead_id.workflow_master_id.workflow_ids:
                if not self.lead_id.checklist_tracking_line:
                    self.is_next_workflow = False
                    defaults.update({
                                    'landoc_stage': workflow.landoc_stage,
                                    'department_id': workflow.department_id.id,
                                    'stage_id': workflow.stage_id.id,
                                    'workflow_line_id': workflow.id,
                                     })
                    self.write(defaults)
                    break
                if workflow.id not in last_workflow_line:
                    self.is_next_workflow = False
                    val_list.update({
                                    'landoc_stage': workflow.landoc_stage,
                                    'department_id': workflow.department_id.id,
                                    'stage_id': workflow.stage_id.id,
                                    'workflow_line_id': workflow.id,
                                     })
                    self.write(val_list)
                    break
            if not defaults and not val_list and self.lead_id.workflow_master_id:
                self.is_next_workflow = True



    def action_checklist_tracking(self):
        previous_landoc_stage = self.lead_id.checklist_tracking_line.filtered(lambda l:l.active_step).landoc_stage or None
        previous_stage = self.lead_id.checklist_tracking_line.filtered(lambda l:l.active_step).stage_id.name or None
        if self.choose_step == 'next_worklow_step' and not self.is_next_workflow and self.lead_id.workflow_master_id:
            workflow_lists = self._next_workflows(self.lead_id)
            line_vals = []
            active_step = True
            seq_next = len(self.lead_id.checklist_tracking_line) + 1
            for sub_workflow in workflow_lists:
                line_vals.append((0, 0, {
                    'lead_id' : self.lead_id.id,
                    'sequence': seq_next,
                    'comments': self.comments,
                    'landoc_stage': sub_workflow.landoc_stage,
                    'department_id': sub_workflow.department_id.id,
                    'assigned_to_id': self.assigned_to_id.id,
                    'stage_id': sub_workflow.stage_id.id,
                    'active_step': active_step,
                    'workflow_line_id': sub_workflow.id
                }))
                active_step = False
                seq_next += 1
            if self.lead_id:
                for rec in self.lead_id.checklist_tracking_line:
                    rec.active_step = False
                self.sudo().lead_id.checklist_tracking_line = line_vals
                self.prev_department_id = self.lead_id.team_id.id
                self.prev_assigned_to_id = self.lead_id.assigned_to_id.id
                self.sudo().lead_id.team_id = self.department_id.id
                self.sudo().lead_id.assigned_to_id = self.assigned_to_id.id
                self.sudo().lead_id.landoc_stage = self.landoc_stage
                active_stpe_id = self.lead_id.checklist_tracking_line.filtered(lambda l: l.active_step)
                if active_stpe_id and self.attachment_file:
                    attachments_ids = self.env['ir.attachment'].create({
                        'name': self.file_name or 'Uploaded File',
                        'type': 'binary',
                        'datas': self.attachment_file,  # base64 value from Binary field
                        'res_model': active_stpe_id._name,
                        'res_id': active_stpe_id.id,
                        # 'mimetype': 'application/octet-stream',  # optional
                    })
                    active_stpe_id.attachment_ids = attachments_ids.ids


        if self.crm_checklist_tracking_id and self.choose_step == 'jump_next_checklist_step':
            for rec in self.lead_id.checklist_tracking_line:
                rec.active_step = False
                if rec.id == self.crm_checklist_tracking_id.id:
                    rec.active_step = True
                    rec.department_status = 'to_do'
                    self.prev_department_id = self.lead_id.team_id.id
                    self.prev_assigned_to_id = self.lead_id.assigned_to_id.id
                    self.sudo().lead_id.team_id = rec.department_id.id
                    self.sudo().lead_id.assigned_to_id = rec.assigned_to_id.id
                    self.sudo().lead_id.landoc_stage = rec.landoc_stage


        if self.is_next_workflow and self.lead_id.workflow_master_id and self.choose_step == 'next_worklow_step':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _("We've completed all the steps in the workflow !"),
                }
            }
        elif not self.lead_id.workflow_master_id and self.choose_step == 'next_worklow_step':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _("There is no workflow configured !"),
                }
            }

        if self.lead_id.team_id.id != self.prev_department_id.id or self.lead_id.assigned_to_id.id != self.prev_assigned_to_id.id:
            crm_kanban_action = self.env['ir.actions.actions']._for_xml_id('crm.crm_lead_action_pipeline')
            crm_kanban_action['target'] = 'main'
            return crm_kanban_action


