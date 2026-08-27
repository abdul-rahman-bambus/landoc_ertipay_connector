# Landoc Odoo 18 Custom Add-ons

This repository contains the Odoo 18 add-ons used by Landoc for service-request
intake, CRM processing, document verification, property valuation, service
delivery, reporting, external automation, payments, and customer communication.
It also vendors several community accounting, user-interface, and telephony
add-ons required by the deployment.

This document is intended to give maintainers and future Codex sessions enough
context to navigate the repository safely. It describes the current code; it is
not a guarantee that every module is installed in every environment.

## Repository map

### Landoc business add-ons

| Module | Role | Important dependencies |
| --- | --- | --- |
| `custom_landoc` | Master data and base configuration for services, workflows, checklists, locations, fees, users, and appointments. | Standard Sales, CRM, HR, Accounting, Expenses, and Purchase modules |
| `custom_crm` | Main Landoc ticket lifecycle built on `crm.lead`, including assignments, workflow/checklist tracking, quotations, invoices, expenses, vendor bills, and service creation. | `custom_landoc`, `partner_city_m2o` |
| `landoc_services` | Detailed execution records for Landoc services, including EC/property and PWD/building details. | `custom_crm`, `property_value_calculation` |
| `landoc_reports` | Printable Landoc service and Encumbrance Certificate reports. | `landoc_services` |
| `property_value_calculation` | Property valuation, stamp-duty/registration-fee calculation, government link, and PWD building details. | `custom_landoc`, `custom_crm` |
| `crm_ticket_expense` | Guided customer/vendor financial actions and employee-expense tracking from a CRM ticket. | `custom_crm` |
| `currency_denomination` | Opening and closing cash denomination records and totals. | `custom_landoc`, `account` |
| `partner_city_m2o` | Structured city master and relational city fields for contacts and companies. | `custom_landoc` |

### Integration and communication add-ons

| Module | Role | Integration surface |
| --- | --- | --- |
| `landoc_n8n_connector` | Connects n8n/chatbot workflows to Landoc lead intake and appointment selection. | Bearer-protected HTTP APIs and Odoo system parameters |
| `payment_ertipay` | Ertipay UPI payment provider, including payment creation, encrypted API traffic, status handling, callbacks, and invoice metadata. | Ertipay API, OpenSSL, Odoo Payment |
| `whatsapp_business` | Meta WhatsApp Business integration for chatter, Discuss, templates, messages, attachments, statuses, and automation. | Meta Graph API and public webhook |
| `audio_file_to_text` | Audio-file transcription and posting of transcribed text to chatter. | FFmpeg, PyAudio, SpeechRecognition |
| `char_audio_widget` | Browser audio-recorder field widget with speech-to-text support and user language preferences. | Browser media APIs and speech-recognition support |

### Vendored community add-ons

These directories are third-party code. Keep Landoc-specific behavior outside
them where possible so upstream updates remain manageable.

| Modules | Upstream/purpose |
| --- | --- |
| `base_account_budget` | Cybrosys analytic budget management for Odoo Community |
| `base_accounting_kit` | Cybrosys Community accounting features, assets, follow-ups, bank tools, and reports |
| `dynamic_accounts_report` | Cybrosys interactive accounting reports on top of `base_accounting_kit` |
| `muk_web_appsbar`, `muk_web_chatter`, `muk_web_colors`, `muk_web_dialog`, `muk_web_theme` | MuK backend navigation, chatter, dialog, color, and theme extensions |
| `voip_oca` | OCA VoIP/PBX integration; excludes the standard `voip` add-on |

### Non-addon artifacts

`n8n_landoc_service_automation_backup/` contains exported n8n Marriage
Registration workflow JSON backups. It has no Odoo manifest and is not an Odoo
add-on.

## Module details

### `custom_landoc`: shared domain and master data

This is the foundation for the Landoc-specific add-ons. It defines:

- service categories and service types;
- workflow masters and ordered workflow lines;
- service/property checklists and checklist metadata;
- districts, zones, villages, Sub-Registrar Offices, religions, and property
  types;
- Landoc fee, service appointment, and service availability records;
- company, settings, user, menu-visibility, department, sequence, and security
  configuration.

Changes to these models or their identifiers can affect CRM intake, n8n
mapping, appointment selection, property calculations, and service processing.

### `custom_crm`: ticket intake and workflow orchestration

The main operational object remains Odoo's `crm.lead`, extended as the Landoc
service request or ticket. The module connects customer/contact information,
service selection, property data, team assignment, workflow state, and
financial records. Major capabilities include:

- request sequencing and customer/address preparation;
- service-category, service, workflow, SRO, zone, district, religion, and
  marriage-registration fields;
- workflow/checklist generation, active-step navigation, department transfer,
  status tracking, and start/stop/pause/resume timers;
- document checklist upload/review, approval, correction, rejection, and n8n
  notifications;
- quotation, invoice, vendor-bill, expense, and analytic links;
- actions to create/open service processing and service bookings;
- extensions to contacts, employees, sale orders, invoices, expenses, stock,
  and analytic accounts.

The module has a Python dependency on `phonenumbers` for mobile validation.

### `landoc_services`: detailed service delivery

`crm.landoc.service` is the detailed processing record linked to the CRM ticket.
It captures service-specific information after intake, including Encumbrance
Certificate survey/subdivision, plot, flat, house, boundary, ownership, and
registered-document details. It also stores PWD floor, construction, flooring,
utility, sanitary, parking, and amenity information.

Confirming a service record interacts with the active CRM checklist/workflow
step. Treat changes to confirmation and step completion as workflow changes,
not merely form changes.

### `property_value_calculation`: valuation and fees

This module extends CRM leads with land area/unit/rate, estimated value, a
configurable government link, and PWD details. It reads fixed or percentage
stamp-duty and registration-fee settings from the selected service and computes
their total. Any change to this calculation must be checked against current
business and statutory rules.

### `landoc_reports`: printed output

This module owns the Landoc service report action and Encumbrance Certificate
report template. Report-specific layout or presentation should normally remain
here instead of being added to `landoc_services`.

### `landoc_n8n_connector`: chatbot and appointment APIs

The connector currently exposes these principal routes:

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/crm/lead` | Create a Landoc request from an automation/chatbot payload; currently contains Marriage Registration-specific mapping |
| `GET` | `/api/v1/service/available-dates` | Return future active availability for a service code |
| `POST` | `/api/v1/service/select-date` | Select a service date and create/update booking context for a lead |

The CRM endpoint validates an `Authorization: Bearer ...` token against the
`landoc_n8n_webhook.api_token` system parameter. Bot identity/session/stage
fields may be supplied either at the payload root or in `bot_details`. Marriage
Registration service codes are matched to `service.type`, then related workflow,
contact, source, configured bot user, and team records are resolved.

Do not publish real tokens or customer payloads in documentation, tests, logs,
or commits. Public-controller changes require explicit authentication,
authorization, input-validation, and response-contract review.

### `payment_ertipay`: UPI payment flow

The Ertipay provider participates in Odoo's normal `payment.provider` and
`payment.transaction` lifecycle. It handles full/partial payable amounts,
gateway charges, API authentication, payload encryption/decryption, payment
creation, status fetching, notification processing, and invoice payment
metadata. Its public routes are:

- `/payment/ertipay/redirect`
- `/payment/ertipay/return`
- `/payment/ertipay/callback`

Provider credentials, base URLs, encryption key/IV, and logging options are
configured on the payment provider. Never hard-code credentials. Preserve
amount validation, transaction lookup, callback idempotency, sensitive-value
masking, and Odoo state transitions when maintaining this module. The UAT
simulation actions are testing aids and must not be confused with production
gateway confirmation.

### `whatsapp_business`: Meta messaging

This add-on manages Meta account credentials, webhook verification, inbound and
outbound messages, delivery/read statuses, contacts, Discuss channels,
attachments, templates, variables, reports, API logs, chatter actions, and
create/write-triggered automation. It exposes GET and POST handlers at
`/whatsapp/webhook/`.

Webhook signature validation and account lookup are security boundaries. Avoid
logging access tokens or full personal-message content, and verify Meta template
and phone-formatting requirements before changing payload construction.

### Other supporting modules

- `crm_ticket_expense` calculates ticket financial status/collection data and
  presents actions for quotations, invoices, customer payments, vendor bills,
  vendor payments, and expenses.
- `currency_denomination` stores opening/closing denomination lines and computes
  line and session totals.
- `partner_city_m2o` provides `res.city` and synchronizes country, state, city,
  and ZIP selections on contacts and companies. Its Indian city XML is master
  data, not demo data.
- `audio_file_to_text` provides file/chatter transcription through a wizard.
- `char_audio_widget` provides the reusable browser recording field widget.

## Dependency and business flow

The central add-on dependency direction is approximately:

```text
custom_landoc
├── partner_city_m2o
│   └── custom_crm
├── custom_crm
│   ├── crm_ticket_expense
│   ├── property_value_calculation
│   │   └── landoc_services
│   │       └── landoc_reports
│   └── landoc_n8n_connector
└── currency_denomination
```

At runtime, the main business flow is:

```text
Landoc master configuration
    → chatbot/API or manual CRM ticket intake
    → workflow and document checklist processing
    → quotation/invoice/expense/payment operations
    → property valuation and detailed service execution
    → service confirmation and printed reports
```

Odoo resolves manifest dependencies automatically. When investigating a change,
start at the module that owns the model and then review every downstream module
that inherits or consumes it.

## External requirements and configuration

Manifest-declared Python/runtime dependencies include:

- `custom_crm`: `phonenumbers`;
- `audio_file_to_text`: FFmpeg, PyAudio, and SpeechRecognition;
- `base_accounting_kit`: `openpyxl`, `ofxparse`, and `qifparse`;
- `payment_ertipay`: an accessible `openssl` executable is used by its encryption
  implementation.

Deployment also requires valid configuration for external systems such as n8n,
Ertipay, and Meta WhatsApp. Configuration and secrets belong in Odoo settings,
system parameters, environment/deployment secret storage, or provider records;
never commit them to this repository.

## Development guidance

1. Read `AGENTS.md` before editing.
2. Identify whether the target is project-owned or vendored code.
3. Review the add-on manifest, model inheritance, security files, views, data,
   controllers, and downstream dependencies before changing behavior.
4. Keep integration payload contracts backward compatible unless a coordinated
   change is explicitly approved.
5. Add or update module-level tests for functional changes. This repository does
   not contain a complete standalone Odoo runtime, so installation/upgrade tests
   normally run in the deployment's Odoo test environment.
6. Never include credentials, tokens, unmasked payment fields, or customer data
   in commits or fixtures.

For an Odoo-enabled environment, validate changed add-ons using the deployment's
normal database and configuration, for example:

```bash
odoo-bin -c /path/to/odoo.conf -d test_database \
  -i module_name --stop-after-init --test-enable

odoo-bin -c /path/to/odoo.conf -d test_database \
  -u module_name --stop-after-init --test-enable
```

Use a disposable test database and replace paths/module names with values for the
target environment.
