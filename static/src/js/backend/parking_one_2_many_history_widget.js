/** @odoo-module **/

import { Component, onWillStart, markup, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { View } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";

export class ParkingBooleanIconField extends Component {
  static template = "parking.BooleanIconField";
  static props = {
    ...standardFieldProps,
    isIn: { type: Boolean, optional: true },
    isContact: { type: Boolean, optional: true },
  };

  static components = { View };

  setup() {
    this.baseViewProps = {
      display: { searchPanel: false },
      editable: false, // readonly
      noBreadcrumbs: true,
      showButtons: false,
      selectRecord: (resId) => this.selectRecord("stock.receipt.card", resId),
    };
    this.actionService = useService("action");
  }

  get viewProps_move_history_in() {
    let domain;
    if (this.props.isContact) {
      domain = [["status", "=", "input"]];
    } else {
      domain = [["status", "=", "input"]];
    }

    const props = {
      ...this.baseViewProps,
      context: {
        tree_view_ref: "t4tek_device_tracking.view_stock_receipt_card_tree",
        create: 0,
      },
      // Ẩn checkbox
      allowSelectors: false,
      type: "list",
      domain: domain,
      resModel: "stock.receipt.card",
      // viewId: this.state.viewIdTree,
      // Ẩn checkbox
    };
    return props;
  }

  get viewProps_move_history_out() {
    let domain;
    if (this.props.isContact) {
      domain = [["status", "=", "output"]];
    } else {
      domain = [["status", "=", "output"]];
    }
    const props = {
      ...this.baseViewProps,
      context: {
        tree_view_ref: "t4tek_device_tracking.view_stock_receipt_card_tree",
        create: 0,
      },
      // Ẩn checkbox
      allowSelectors: false,
      type: "list",
      domain: domain,
      resModel: "stock.receipt.card",
      // viewId: this.state.viewIdTree,
      // Ẩn checkbox
    };
    return props;
  }

  update() {
    this.props.record.update({
      [this.props.name]: !this.props.record.data[this.props.name],
    });
  }

  selectRecord(resModel, resId) {
    this.actionService.doAction({
      name: "Thông tin chi tiết",
      type: "ir.actions.act_window",
      res_model: resModel,
      views: [[false, "form"]],
      res_id: resId,
      view_mode: "form",
      target: "new",
      context: { create: false, edit: false },
    });
  }
}

export const parkingBooleanIconField = {
  component: ParkingBooleanIconField,
  displayName: _t("Boolean Icon"),
  useSubView: true,
  supportedTypes: ["one2many", "many2many", "boolean"],
  supportedOptions: [
    {
      label: _t("Is In"),
      name: "isIn",
      type: "boolean",
    },
    {
      label: _t("Is Contact"),
      name: "isContact",
      type: "boolean",
    },
  ],
  extractProps: ({ attrs, options }) => ({
    //isIn: attrs.isIn,
    isIn: options.isIn,
    isContact: options.isContact,
  }),
};

registry
  .category("fields")
  .add("parking_one_2_many_history", parkingBooleanIconField);
