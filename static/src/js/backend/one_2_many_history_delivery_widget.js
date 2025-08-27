/** @odoo-module **/

import { Component, onWillStart, markup, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { View } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";

export class BooleanIconFieldDelivery extends Component {
  static template = "t4tek.BooleanIconFieldDelivery";
  static props = {
    ...standardFieldProps,
    type: { type: Text, optional: true },

  };

  static components = { View };

  setup() {
    this.baseViewProps = {
      display: { searchPanel: false },
      editable: false, // readonly
      noBreadcrumbs: true,
      showButtons: false,
      context: {
        tree_view_ref: "stock.vpicktree",
        create: 0,
        column_invisible: 1,
        contact_display: 'partner_address',
        restricted_picking_type_code: 'outgoing',
        search_default_delivery: 1,
        is_oper: true,
        from_menu: 1,
        outgoing: 1,
        default_is_device_tracking: true,
      },
      selectRecord: (resId) => this.selectRecord("stock.picking", resId),
      allowSelectors: false,
      type: "list",
      resModel: "stock.picking",

    };
    this.actionService = useService("action");
  }

  get viewProps_return_output() {
    let domain;
    domain = [["t4tek_stock_picking_type_outgoing", "=", "return_output"], ['is_device_tracking', '=', true]];

    const props = {
      ...this.baseViewProps,
      domain: domain,
      resModel: "stock.picking",
    };
    return props;
  }

  get viewProps_ware_output() {
    let domain;
    domain = [["t4tek_stock_picking_type_outgoing", "=", "ware_output"], ['is_device_tracking', '=', true]];

    const props = {
      ...this.baseViewProps,
      domain: domain,
      resModel: "stock.picking",
    };
    return props;
  }
  get viewProps_sale_output() {
    let domain;
    domain = [["t4tek_stock_picking_type_outgoing", "=", "sale_output"], ['is_device_tracking', '=', true]];

    const props = {
      ...this.baseViewProps,
      domain: domain,
      resModel: "stock.picking",
    };
    return props;
  }
  get viewProps_warranty_after_output() {
    let domain;
    domain = [["t4tek_stock_picking_type_outgoing", "=", "warranty_after_output"], ['is_device_tracking', '=', true]];

    const props = {
      ...this.baseViewProps,
      domain: domain,
      resModel: "stock.picking",
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

export const booleanIconField = {
  component: BooleanIconFieldDelivery,
  displayName: _t("Boolean Icon"),
  useSubView: true,
  supportedTypes: ["one2many", "many2many", "boolean"],
  supportedOptions: [
    {
      label: _t("Type"),
      name: "type",
      type: "Text",
    },
  ],
  extractProps: ({ attrs, options }) => ({
    //isIn: attrs.isIn,
    type: options.type,
  }),
};

registry
  .category("fields")
  .add("one_2_many_history_delivery_widget", booleanIconField);
