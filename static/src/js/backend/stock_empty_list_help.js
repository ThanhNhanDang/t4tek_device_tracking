/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ListController } from "@web/views/list/list_controller";
import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

import { useActionLinks } from "@web/views/view_hook";

export class StockListController extends ListController {
  setup() {
    super.setup();
    // Services cần thiết
    this.notification = useService("notification");
    this.company = useService("company");

    // Timer configuration
    this.refreshInterval = 5000; // 30 giây (có thể config)
    this.timerActive = true;
    this.intervalId = null;

    this.personErrorBlackListSound = new Audio(
      "/t4tek_device_tracking/static/audio/person_error_black.wav"
    );

    this.env.services.bus_service.addChannel("12344");
    this.env.services.bus_service.subscribe("card_notification", (event) => {
      this.personErrorBlackListSound.play();
    });

    // Setup timer khi component mount
    // onMounted(() => {
    //   this.startAutoRefresh();
    // });

    // // Cleanup timer khi component unmount
    // onWillUnmount(() => {
    //   this.stopAutoRefresh();
    // });
  }

  /**
   * Bắt đầu auto refresh timer
   */
  startAutoRefresh() {
    if (this.intervalId) {
      this.stopAutoRefresh();
    }

    this.intervalId = setInterval(async () => {
      if (this.timerActive) {
        await this.refreshData();
      }
    }, this.refreshInterval);

    // console.log(`Auto refresh started - interval: ${this.refreshInterval}ms`);
  }

  /**
   * Dừng auto refresh timer
   */
  stopAutoRefresh() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
      // console.log('Auto refresh stopped');
    }
  }

  /**
   * Refresh dữ liệu
   */
  async refreshData() {
    try {
      // console.log('Auto refreshing data...');
      await this.model.load();


      // Optional: Show notification
      // this.notification.add("Dữ liệu đã được cập nhật", {
      //     type: "info",
      //     sticky: false,
      // });
    } catch (error) {
      console.error("Error refreshing data:", error);

      // Optional: Show error notification
      this.notification.add("Lỗi khi cập nhật dữ liệu", {
        type: "danger",
        sticky: false,
      });
    }
  }

  /**
   * Toggle auto refresh on/off
   */
  toggleAutoRefresh() {
    this.timerActive = !this.timerActive;

    if (this.timerActive) {
      this.notification.add("Auto refresh: Bật", { type: "success" });
    } else {
      this.notification.add("Auto refresh: Tắt", { type: "warning" });
    }
  }

  /**
   * Manual refresh
   */
  async onManualRefresh() {
    await this.refreshData();
    this.notification.add("Đã làm mới dữ liệu thủ công", { type: "success" });
  }

  /**
   * Set refresh interval
   */
  setRefreshInterval(seconds) {
    this.refreshInterval = seconds * 1000;

    // Restart timer với interval mới
    if (this.intervalId) {
      this.stopAutoRefresh();
      this.startAutoRefresh();
    }

    this.notification.add(`Đã đặt thời gian refresh: ${seconds}s`, {
      type: "info",
    });
  }

  /**
   * Override onRecordClick để tạm dừng timer khi user tương tác
   */
  async onRecordClick(record, params) {
    // Tạm dừng timer khi user click vào record
    this.timerActive = false;

    await super.onRecordClick(record, params);

    // Bật lại timer sau 5 giây
    setTimeout(() => {
      this.timerActive = true;
    }, 5000);
  }

  /**
   * Pause timer khi user đang tương tác với form
   */
  pauseTimerTemporary(duration = 10000) {
    this.timerActive = false;

    setTimeout(() => {
      this.timerActive = true;
    }, duration);
  }
}

export const StockListView = {
  ...listView,
  Controller: StockListController,
};

registry.category("views").add("t4tek_stock_list_view", StockListView);
