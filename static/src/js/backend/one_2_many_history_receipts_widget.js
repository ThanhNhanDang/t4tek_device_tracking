/** @odoo-module **/

import { Component, onWillStart, markup, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { View } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";

export class BooleanIconFieldReceipt extends Component {
  static template = "t4tek.BooleanIconFieldReceipt";
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
        restricted_picking_type_code: 'incoming',
        search_default_reception: 1,
        is_oper: true,
        from_menu: 1,
        outgoing: 0,
        default_is_device_tracking: true,
      },
      selectRecord: (resId) => this.selectRecord("stock.picking", resId),
      allowSelectors: false,
      type: "list",
      resModel: "stock.picking",
    };
    this.actionService = useService("action");
  }

  get viewProps_first_input() {
    let domain;
    domain = [["t4tek_stock_picking_type_incoming", "=", "first_input"], ['is_device_tracking', '=', true]];

    const props = {
      ...this.baseViewProps,
      domain: domain,
      resModel: "stock.picking",
    };
    return props;
  }

  get viewProps_re_input() {
    let domain;
    domain = [["t4tek_stock_picking_type_incoming", "=", "re_input"], ['is_device_tracking', '=', true]];

    const props = {
      ...this.baseViewProps,
      domain: domain,
      resModel: "stock.picking",
    };
    return props;
  }
  get viewProps_warranty_input() {
    let domain;
    domain = [["t4tek_stock_picking_type_incoming", "=", "warranty_input"], ['is_device_tracking', '=', true]];

    const props = {
      ...this.baseViewProps,
      domain: domain,
      resModel: "stock.picking",
    };
    return props;
  }
  get viewProps_fisnish_good_input() {
    let domain;
    domain = [["t4tek_stock_picking_type_incoming", "=", "fisnish_good_input"], ['is_device_tracking', '=', true]];

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
  component: BooleanIconFieldReceipt,
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
  .add("one_2_many_history_receipts_widget", booleanIconField);
