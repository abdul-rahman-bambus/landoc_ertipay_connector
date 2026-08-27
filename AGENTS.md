# Codex repository guidance

## Scope

These instructions apply to the entire repository. This is an Odoo 18 add-ons
repository. Read the root `README.md` for module ownership, dependencies, API
surfaces, and the current Landoc business flow before making changes.

## Repository boundaries

- Project-owned business modules are `custom_landoc`, `custom_crm`,
  `landoc_services`, `landoc_reports`, `property_value_calculation`,
  `crm_ticket_expense`, `currency_denomination`, and `partner_city_m2o`.
- Project-owned integration/communication modules are `landoc_n8n_connector`,
  `payment_ertipay`, `whatsapp_business`, `audio_file_to_text`, and
  `char_audio_widget`.
- Treat `base_account_budget`, `base_accounting_kit`,
  `dynamic_accounts_report`, `muk_web_*`, and `voip_oca` as vendored third-party
  modules. Do not add Landoc business behavior to them unless the task explicitly
  requires it. Keep any unavoidable vendor patch narrow and documented.
- `n8n_landoc_service_automation_backup` contains workflow exports and is not an
  Odoo add-on.

## Change workflow

1. Check `git status` and do not overwrite unrelated user changes.
2. Inspect the affected `__manifest__.py`, `__init__.py`, inherited models,
   security/access files, XML views/data, controllers, and downstream modules.
3. Keep changes inside the module that owns the concern. Avoid unrelated cleanup
   or formatting changes.
4. Preserve Odoo 18 APIs and existing external payload/response contracts unless
   the task explicitly approves a breaking change.
5. For a functional model change, consider access rights, record rules, field
   tracking, computed-field dependencies/storage, multi-company behavior,
   onchange versus persisted behavior, upgrades of existing data, and tests.
6. For XML changes, validate XML syntax and referenced external IDs. For Python
   changes, compile the changed files before running the relevant Odoo tests.
7. Summarize tests and any unavailable environment-dependent validation clearly.

## Sensitive areas

- Treat `payment_ertipay` as payment- and accounting-sensitive. Preserve amount
  checks, callback idempotency, notification-to-transaction matching, encryption,
  masked logging, and valid Odoo transaction state transitions.
- Treat n8n and WhatsApp controllers as public integration boundaries. Review
  authentication/authorization, signature or token validation, `sudo()` use,
  input validation, error disclosure, personal data, and replay/idempotency risks.
- Never commit API tokens, credentials, encryption keys/IVs, production URLs with
  embedded secrets, real customer payloads, or unmasked payment information.
- Workflow/checklist confirmation can alter active CRM steps. Trace the full
  `custom_crm` → `landoc_services` flow before changing transitions.
- Property fee and valuation formulas may encode business or statutory rules.
  Do not change them without explicit requirements.

## Odoo conventions

- Follow the style already used by the target module and standard Odoo ORM
  patterns. Do not wrap imports in `try`/`except` blocks.
- Register new Python files through the appropriate `__init__.py`; register views,
  security, data, and reports in dependency-safe manifest order.
- Add access controls for new persistent or transient models as appropriate.
- Use translations for user-facing Python strings and avoid exposing exception or
  secret details through public endpoints.
- Avoid hard-coded record IDs. Prefer XML IDs, configuration parameters, or
  explicit model searches with well-defined failure behavior.
- Use explicit logging without secrets or unnecessary personal data.
- Keep custom JavaScript compatible with Odoo 18's module/component conventions
  and include it in the correct asset bundle.

## Validation

Run the narrowest relevant checks first, followed by an install/upgrade test in
an Odoo-enabled environment when functionality changes. Typical checks include:

```bash
python -m compileall changed_module
python - <<'PY'
import pathlib
import xml.etree.ElementTree as ET

for path in pathlib.Path("changed_module").rglob("*.xml"):
    ET.parse(path)
    print(path)
PY
odoo-bin -c /path/to/odoo.conf -d disposable_test_db \
  -i changed_module --stop-after-init --test-enable
odoo-bin -c /path/to/odoo.conf -d disposable_test_db \
  -u changed_module --stop-after-init --test-enable
```

The exact Odoo command, executable path, configuration, database, and dependency
installation are environment-specific. Never run install/upgrade validation
against production data.

For documentation-only changes, inspect the rendered Markdown where possible,
check whitespace with `git diff --check`, and verify that the diff contains only
the approved documentation files.
