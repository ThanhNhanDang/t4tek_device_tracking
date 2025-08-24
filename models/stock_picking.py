import logging

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    is_device_tracking = fields.Boolean(default=False, string='Theo dõi thiết bị')
    image_tracking = fields.Image("Hình ảnh xác minh", max_width=1024, max_height=1024)
    stock_receipt_id = fields.Many2one('stock.receipt', string='Phiếu Ghi Nhận', required=False, ondelete='cascade')
    
    def action_generate_cards(self):
        if not self.stock_receipt_id:
            raise ValidationError(_("Phiếu Ghi Nhận Chưa Có."))
        return self.stock_receipt_id.action_generate_cards()
    
    
    def action_scan_cards(self):
        _logger.info("action_scan_cards called for picking: %s", self.env.context.get('uuid_client'))
        if self.env.context.get('uuid_client', False):
            self.env['bus.bus'].sudo()._sendone(
                self.env.context.get('uuid_client', False),
                'notification',
                {
                    "type":"scan_cards",
                    "id":self.id,
                    "model": self._name,
                    'receipt_name': self.name,
                    'receipt_type': self.picking_type_code,
                }
            )
    def callback_scan_cards(self, tags):
        """Callback function to process scanned RFID tags"""
        if not tags:
            return "Không có thẻ nào được quét!"
        
        records = []
        lot_ids = []
        error_messages = []
        
        for tag in tags:
            # Kiểm tra tag có đúng format không
            if not isinstance(tag, dict) or 'Tid' not in tag:
                error_messages.append("Format thẻ không hợp lệ!")
                continue
                
            # Tìm stock receipt card
            card_record = self.env['stock.receipt.card'].search([
                ('name', '=', tag['Tid']),
            ], limit=1)
            
            if not card_record:
                error_messages.append(f"Sản phẩm có mã {tag['Tid']} không tồn tại trong hệ thống.")
                continue
                
            records.append(card_record)
            
            # Tìm stock lot tương ứng
            lot = self.env['stock.lot'].search([
                ('name', '=', tag['Tid']),
            ], limit=1)
            
            if lot:
                lot_ids.append(lot.id)
            else:
                # Nếu không tìm thấy lot, có thể tạo mới hoặc bỏ qua
                # Tùy thuộc vào logic nghiệp vụ
                lot_ids.append(False)
        
        # Nếu có lỗi trong quá trình scan
        if error_messages:
            return '; '.join(error_messages)
        
        # Nếu không có records nào hợp lệ
        if not records:
            return "Không tìm thấy sản phẩm hợp lệ nào!"
        
        # Xử lý xuất kho nếu là picking type outgoing
        if self.picking_type_code == 'outgoing':
            try:
                # Chuyển đổi list thành recordset
                card_recordset = self.env['stock.receipt.card'].browse([r.id for r in records])
                
                # Gọi method xuất kho
                result = card_recordset.action_export_cards_v2(
                    picking=self,
                    lot_ids=lot_ids
                )
                
                return result if result else "1"
                
            except Exception as e:
                return f"Lỗi khi xuất kho: {str(e)}"
        elif self.picking_type_code == 'incoming':
            try:
                # Chuyển đổi list thành recordset
                card_recordset = self.env['stock.receipt.card'].browse([r.id for r in records])
                
                # Gọi method xuất kho
                result = card_recordset.action_import_cards_v2(
                    picking=self,
                    lot_ids=lot_ids
                )
                
                return result if result else "1"
                
            except Exception as e:
                return f"Lỗi khi xuất kho: {str(e)}"
        
        return "1"
    def button_validate(self):
        """Override button_validate để bắt buộc upload hình ảnh cho device tracking"""
        if self.is_device_tracking:
            if self.env.context.get('from_menu', False):
                _logger.info("button_validate called from menu for picking: %s", self.env.context.get('uuid_client'))
                 # Kiểm tra xem đã có hình ảnh chưa
                if not self.image_tracking:
                    # Mở wizard để upload hình ảnh
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Upload Hình Ảnh Xác Minh'),
                        'res_model': 'stock.action.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_picking_id': self.id,
                        }
                    }
                else:
                    # Đã có hình ảnh, tiếp tục validate bình thường
                    return super(StockPicking, self).button_validate()
            if not self.stock_receipt_id:
                raise ValidationError(_("Phiếu Ghi Nhận Chưa Có."))
            
            if self.stock_receipt_id.state == 'draft':
                raise ValidationError(_("Phiếu Ghi Nhận Chưa Ở Trạng Thái Xác Nhận."))
            
            # Kiểm tra xem đã có hình ảnh chưa
            if not self.image_tracking:
                # Mở wizard để upload hình ảnh
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Upload Hình Ảnh Xác Minh'),
                    'res_model': 'stock.action.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_picking_id': self.id,
                    }
                }
            else:
                # Đã có hình ảnh, tiếp tục validate bình thường
                return super(StockPicking, self).button_validate()
        else:
            # Không phải device tracking, validate bình thường
            return super(StockPicking, self).button_validate()