/** @odoo-module */

import {registry} from "@web/core/registry";

import {formView} from "@web/views/form/form_view";
import {FormController} from "@web/views/form/form_controller";

import {onMounted} from '@odoo/owl'

export class StockActionWizard extends FormController {
	setup() {
		super.setup();
		console.log(this)
		onMounted(() => {
			const dialog = document.querySelector(".modal-dialog");
			if (dialog) {
				dialog.classList.remove("modal-lg");
				dialog.classList.add("modal-md");
			}
		});
	}
}

registry.category("views").add("stock_action_wizard", {
	...formView,
	Controller: StockActionWizard,
});
