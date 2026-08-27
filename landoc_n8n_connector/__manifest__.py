{
    'name': 'Landoc N8N Connector',
    'version': '18.0.1.0.0',
    'category': 'Service',
    'summary': 'N8N Connector',
    'description': """
        Connects n8n and chatbot workflows with Landoc CRM. It provides
        bearer-token-protected endpoints for service-request intake, specialized
        Marriage Registration mapping, service availability lookup, appointment
        date selection, and chatbot session context on CRM and payment records.
    """,
    'author': 'Bambus Technologies LLP',
    'sequence': 1,
    'website': 'https://bambustechnologies.in/',
    'depends': [
        'base', 'sale', 'crm', 'custom_crm', 'contacts', 'partner_city_m2o', 'custom_landoc', 'sales_team', 'payment',
    ],
    'data': [
        'data/webhook_token.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': True,
}
