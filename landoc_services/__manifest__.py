{
    "name": "CRM Landoc Service",
    "version": "1.0.0",
    "category": "Extra Tools",
    "summary": "CRM Landoc Service",
    "sequence": "1",
    "author": "Bambus Technologies",
    "depends": ["base", 'crm', "custom_landoc", "custom_crm", "property_value_calculation"],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_lead.xml",
        "views/crm_landoc_service_view.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3"
}
