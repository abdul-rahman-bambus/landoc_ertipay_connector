{
    "name": "Landoc Reports",
    "version": "18.0.1.0.0",
    "summary": "Landoc Reports",
    "description": """
        Adds printable reports for Landoc service-processing records, including
        the Encumbrance Certificate report action and template exposed from the
        Landoc service form.
    """,
    "author": "Bambus Technologies LLP",
    "website": "",
    "sequence": 1,
    "license": "OPL-1",
    "category": "Extra Tools",
    "depends": ["base", "crm", "custom_landoc", "custom_crm", "landoc_services"],
    "data": [
        "reports/ir_actions_report.xml",
        "reports/ir_actions_ec_report_template.xml",
        "views/crm_landoc_service_view.xml",
    ],
    "application": True,
    "auto_install": False,
    "installable": True,
}
