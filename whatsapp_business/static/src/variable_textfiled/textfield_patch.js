/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { TextField } from "@web/views/fields/text/text_field";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { usePopover } from "@web/core/popover/popover_hook";
import { browser } from "@web/core/browser/browser";
import { useRef } from "@odoo/owl";

const MAX_VARIABLES = 10;

class WhatsappBusinessTextFieldComponent extends TextField {
    static template = "whatsapp_business.VariablesTextField";
    static components = { ...TextField.components };

    setup() {
        super.setup();
        this.textareaRef = useRef("textarea");
        this.variablesButton = useRef("customVariablesButton");
        this.popover = usePopover(Tooltip, { animation: false, position: "top" });
    }

    _onClickVariablesButton() {
        const textarea = this.textareaRef.el;
        const textFieldContent = textarea.value;
        const matches = textFieldContent.match(/{{\d+}}/g);
        const count = matches ? matches.length + 1 : 0;

        if (count > MAX_VARIABLES) {
            this.popover.open(this.variablesButton.el, { tooltip: _t("Maximum limit reached.") });
            browser.setTimeout(() => this.popover.close(), 1900);
            return;
        }

        if (count === 0) {
            this._insertVariable(textarea, textFieldContent, 1);
        } else {
            this._insertVariable(textarea, textFieldContent, count);
        }
    }

    _insertVariable(textarea, content, variableNumber) {
        textarea.value = `${content} {{${variableNumber}}}`;
        ["input", "change"].forEach(eventType =>
            textarea.dispatchEvent(new Event(eventType, { bubbles: true }))
        );
    }
}

export const WhatsappBusinessTextField = {
    component: WhatsappBusinessTextFieldComponent,
    additionalClasses: [...(TextField.additionalClasses || []), "o_field_text"],
};

registry.category("fields").add("whatsapp_business_variables", WhatsappBusinessTextField);



