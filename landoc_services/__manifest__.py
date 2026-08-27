{
    "name": "CRM Landoc Service",
    "version": "18.0.1.0.0",
    "category": "Extra Tools",
    "summary": "CRM Landoc Service",
    "description": """
        Creates detailed Landoc service-processing records linked to CRM
        tickets. It captures Encumbrance Certificate property details, survey
        and boundary information, PWD building and floor details, amenities,
        and service confirmation tied to the active CRM workflow step.
    """,
    "sequence": 1,
    "author": "Bambus Technologies",
    "depends": ["base", "crm", "custom_landoc", "custom_crm", "property_value_calculation"],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_lead.xml",
        "views/crm_landoc_service_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
