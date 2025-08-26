/** @odoo-module **/
import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

import { ListRenderer } from "@web/views/list/list_renderer";

export class O2MListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.td_footer_num = [1]
    }

    get nbCols() {
        let nbCols = this.columns.length;
        if (this.hasSelectors) {
            nbCols++;
        }
        if (this.hasActionsColumn) {
            nbCols++;
        }
        if (this.hasOpenFormViewColumn) {
            nbCols++;
        }
        return nbCols + 1;
    }
}

O2MListRenderer.template = "NoListRenderer"
O2MListRenderer.recordRowTemplate = "NoListRendererRecordRow";


export class NoColumnOne2ManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: O2MListRenderer,
    }
    setup() {
        super.setup();
    }

}

export const noColumnOne2many = {
    ...x2ManyField,
    component: NoColumnOne2ManyField,
};

// Register the field
registry.category("fields").add("no_column_one2many", noColumnOne2many);