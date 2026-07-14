# WhatsApp Business Integration for Odoo

## Overview
This module integrates WhatsApp Business API with Odoo, enabling automated and manual WhatsApp messaging, template management, and real-time message tracking directly from Odoo. It is designed for businesses to streamline communication with customers using WhatsApp, leveraging Odoo's models, automation, and UI.

## Features
- **WhatsApp Account Management**: Configure multiple WhatsApp Business accounts, manage API credentials, webhook URLs, and test connections.
- **Message Templates**: Create, validate, submit, update, and delete WhatsApp message templates. Supports rich content (text, images, documents, location, quick replies, buttons).
- **Automated Messaging**: Trigger WhatsApp messages based on Odoo model events (e.g., sales, contacts) using templates and automation rules.
- **Manual Messaging**: Send WhatsApp messages manually from Odoo records using pre-defined templates.
- **Message Logging**: Track sent and received messages, delivery status, and errors. View message history and logs in Odoo.
- **Webhook Integration**: Receive and process incoming WhatsApp messages, status updates, and reactions via webhooks.
- **Media Handling**: Upload and send images, documents, audio, and video files via WhatsApp.
- **User Notifications**: Notify Odoo users about WhatsApp events and message statuses.
- **Security & Access Control**: Role-based access for users and managers, with configurable permissions.
- **UI Enhancements**: Custom views, widgets, and preview features for WhatsApp messages and templates.

## Main Components
- **Models**:
  - `whatsapp.account.details`: WhatsApp account configuration and API credentials.
  - `template.whatsapp`: WhatsApp message template management.
  - `whatsapp.message.info`: Message log and tracking.
  - `whatsapp.api.services`: API communication and request handling.
  - `whatsapp_automation`, `whatsapp_variable`, etc.: Automation and variable support for dynamic templates.
- **Controllers**:
  - Webhook endpoint for WhatsApp API callbacks (message delivery, status, template changes).
- **Wizards**:
  - Message preview and manual sending via Odoo UI.
- **Views**:
  - Tree, form, and search views for accounts, templates, and messages.
  - Custom widgets for template variables, file uploads, and preview.
- **Security**:
  - Groups and access rights for users and managers.

## Flow & Usage
1. **Setup WhatsApp Account**:
   - Go to WhatsApp Business > Account Details.
   - Add your WhatsApp Business API credentials, phone number ID, and webhook token.
   - Test the connection to verify credentials.
2. **Create Message Templates**:
   - Go to WhatsApp Business > Template.
   - Create a new template, define content, variables, header/footer, and buttons.
   - Validate and submit the template to WhatsApp for approval.
   - Update or delete templates as needed.
3. **Automate Messaging**:
   - Link templates to Odoo models (e.g., sales, contacts).
   - Configure triggers and automation rules.
   - Messages are sent automatically when conditions are met.
4. **Manual Messaging**:
   - Use the wizard to preview and send WhatsApp messages from Odoo records.
5. **Track Messages**:
   - View message logs, delivery status, and errors in WhatsApp Business > Messages.
   - Receive incoming messages and reactions via webhook.

## Technical Details
- **API Communication**: Uses Facebook Graph API endpoints for WhatsApp Business.
- **Webhook**: `/whatsapp/webhook/` endpoint for GET (verification) and POST (message/status updates).
- **Media Uploads**: Supports file uploads for images, documents, and other media types.
- **Template Variables**: Dynamic fields and placeholders for personalized messages.
- **Automation**: Triggers based on Odoo model field changes and events.

## Configuration
- Set up WhatsApp Business API credentials in Account Details.
- Configure webhook URL in Facebook Developer Console to point to `/whatsapp/webhook/`.
- Define message templates and link to Odoo models.
- Set user permissions as needed.

## Assets
- Custom JS and SCSS for UI enhancements.
- Static images for message previews and icons.

## License
LGPL-3

## Author
Bambus Technologies LLP

## Support
For issues or support, contact [Bambus Technologies LLP](https://bambustechnologies.in/).
