{
    "name": "Property Value Calculation",
    "version": "18.0.1.0.0",
    "summary": "Property Value Calculation",
    "description": """
        Adds property valuation fields and calculations to Landoc CRM tickets.
        It supports land measurements, estimated values, fixed or percentage
        stamp duty and registration fees, government links, and detailed PWD
        building, floor, and amenity information.
    """,
    "author": "Bambus Technologies LLP",
    "website": "",
    "sequence": "1",
    "license": "OPL-1",
    "category": "Extra Tools",
    "depends": ["base", "crm", "custom_landoc", "custom_crm"],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_lead.xml",
        "views/services.xml",
    ],
    "application": True,
    "auto_install": False,
}
