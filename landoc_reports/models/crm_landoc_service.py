from odoo import fields, models, api, _
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)


class CrmLandocService(models.Model):
    _inherit = 'crm.landoc.service'

    ec_template_data = fields.Binary(compute='_compute_ec_template_data')

    def _compute_ec_template_data(self):
        """
        Compute EC template data for Encumbrance Certificate (EC).
        """
        today = datetime.now().strftime('%d-%m-%Y')
        user_name = self.env.user.name

        for record in self:
            data = {
                "current_date": today,
                "current_user": user_name,
                "total_extent": f"{record.total_extent} {'ac' if record.extent_sqft_or_area == 'acre' else 'sq ft'}",
                "conveyed_extent": f"{record.conveyed_extent} {'ac' if record.extent_sqft_or_area == 'acre' else 'sq ft'}",
                "undivided_share": f"{record.undivided_share} {'ac' if record.extent_sqft_or_area == 'acre' else 'sq ft'}",
                "build_up_area": f"{record.build_up_area} {'ac' if record.extent_sqft_or_area == 'acre' else 'sq ft'}",
            }

            # --- Master fields ---
            if record.zone_id:
                data["ec_zone_id"] = record.zone_id.name
            if record.district_id:
                data["ec_district_id"] = record.district_id.name
            if record.sro_id:
                data["ec_sro_id"] = record.sro_id.name

            # --- EC period ---
            if record.ec_start_date and record.ec_end_date:
                data["ec_period"] = (
                    f"{record.ec_start_date.strftime('%d-%m-%Y')} to "
                    f"{record.ec_end_date.strftime('%d-%m-%Y')}"
                )

            # --- Survey details ---
            if record.survey_details_line:
                data["survey_details_line"] = [
                    {
                        "ec_village_name": line.ec_village_id.name,
                        "survey_no": line.survey_no,
                        "sub_division_no": line.sub_division_no,
                    }
                    for line in record.survey_details_line
                ]

            # --- Plot / Flat ---
            if record.plot_details_line:
                data["plot_details_line"] = ", ".join(
                    record.plot_details_line.mapped("ec_plot_no")
                )

            if record.flat_details_line:
                data["flat_details_line"] = ", ".join(
                    record.flat_details_line.mapped("ec_flat_no")
                )

            # --- House details ---
            if record.house_details_line:
                data["house_details_line"] = [
                    {
                        "ec_door_no": line.ec_door_no,
                        "ec_ward_no": line.ec_ward_no,
                        "ec_block_no": line.ec_block_no,
                    }
                    for line in record.house_details_line
                ]

            # --- Boundary details ---
            if record.boundary_details_line:
                data["boundary_details_line"] = [
                    {
                        "ec_east": line.ec_east,
                        "ec_west": line.ec_west,
                        "ec_north": line.ec_north,
                        "ec_south": line.ec_south,
                    }
                    for line in record.boundary_details_line
                ]

            # --- Optional fields ---
            optional_fields = {
                "old_survey_or_sub_div_no": record.old_survey_or_sub_div_no,
                "t_s_no": record.t_s_no,
                "old_door_no": record.old_door_no,
                "name_of_declared_owner": record.name_of_declared_owner,
                "father_name": record.father_name,
                "any_other_relevant_info": record.any_other_relevant_info,
                "any_registered_document_no": record.any_registered_document_no,
            }

            data.update({k: v for k, v in optional_fields.items() if v})

            record.ec_template_data = data


    def action_print_ec(self):
        """
        Print EC template data for Encumbrance Certificate (EC).
        """
        return self.env.ref(
            'landoc_reports.action_report_crm_landoc_service_ec'
        ).report_action(self)



