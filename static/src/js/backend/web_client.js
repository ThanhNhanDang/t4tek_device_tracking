/** @odoo-module **/
import { WebClient } from "@web/webclient/webclient";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { onWillStart, useState, onMounted } from "@odoo/owl";
patch(WebClient.prototype, {
  setup() {
    super.setup();
  },

  async _loadDefaultApp() {
    // Selects the first root menu if any
    let root;
    let firstApp;
    if (await user.hasGroup("base.group_system"))
      return super._loadDefaultApp();

    if (await user.hasGroup("t4tek_device_tracking.operator")) {
      const filteredArray = this.menuService
        .getApps()
        .filter(
          (item) => item.xmlid === "t4tek_device_tracking.operator_view_root"
        );
      root = filteredArray[0];
      firstApp = root.appID;
    } else {
      root = this.menuService.getMenu("root");
      firstApp = root.children[0];
    }
    if (firstApp) {
      return this.menuService.selectMenu(firstApp);
    }
  },
});
