{
    'name': 'CRM Ticket Expenses',
    'category': 'CRM',
    'summary': 'Link employee expenses to CRM Leads (Tickets)',
    'description': """
        This module links expenses with CRM leads or tickets
        allowing expense tracking per ticket.
    """,
    'depends': ['base', 'crm', 'account', 'hr_expense', 'custom_crm'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
        'views/hr_expense_views.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
}
