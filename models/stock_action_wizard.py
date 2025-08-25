import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class StockActionWizard(models.TransientModel):
    _name = 'stock.action.wizard'
    _description = 'Stock Action Wizard for Image Upload'

    # Thay đổi từ file_attachment thành image_attachment
    image_attachment = fields.Image(
        'Hình Ảnh Xác Minh', 
        help="Tải lên hình ảnh xác minh (.jpg, .png, .jpeg)",
        max_width=1024, 
        max_height=1024
    )
    
    picking_id = fields.Many2one(
        'stock.picking', 
        string='Stock Picking',
        required=False
    )
    
    def action_confirm(self):
        """Confirm the action and save image to picking then validate"""
        
        if not self.picking_id:
            raise UserError(_('Không tìm thấy phiếu kho.'))

        picking = self.picking_id
        
        # Validate image is uploaded
        if not self.image_attachment:
            raise UserError(_('Vui lòng tải lên hình ảnh xác minh.'))
        
        # Save image to picking
        picking.image_tracking = self.image_attachment
        
        # Log the action
        _logger.info(f"Image uploaded for picking {picking.name}")
        
        # Sau khi lưu hình ảnh, gọi button_validate gốc
        try:
            result = picking.button_validate()
            if picking.stock_receipt_id:
                picking.stock_receipt_id.write({'state': 'done'})
                picking.stock_receipt_id.card_ids.write({'is_used': True})
            elif picking.picking_type_code == 'outgoing':
                lot_ids= picking.move_ids_without_package.mapped('lot_id')
                if lot_ids:
                    self.env['stock.receipt.card'].search([('name', 'in', lot_ids.mapped('name'))]).write({'status': 'output'})
            elif picking.picking_type_code == 'incoming':
                lot_ids= picking.move_ids_without_package.mapped('lot_id')
                if lot_ids:
                    self.env['stock.receipt.card'].search([('name', 'in', lot_ids.mapped('name'))]).write({'status': 'input'})
            # Nếu button_validate trả về wizard (như immediate transfer wizard)
            if isinstance(result, dict) and result.get('res_model'):
                return result
            
            # Nếu validate thành công, hiển thị thông báo
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Thành Công'),
                    'message': _('Đã tải hình ảnh và xác nhận phiếu kho thành công.'),
                    'type': 'success',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.act_window_close',
                    }
                }
            }
            
        except Exception as e:
            # Nếu có lỗi trong quá trình validate, xóa hình ảnh đã lưu
            picking.image_tracking = False
            raise UserError(_('Lỗi khi xác nhận phiếu kho: %s') % str(e))
    
    def action_cancel(self):
        """Cancel and close wizard"""
        return {'type': 'ir.actions.act_window_close'}
