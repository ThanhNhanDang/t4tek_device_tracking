import logging

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
_logger = logging.getLogger(__name__)
from odoo.addons.web.controllers.utils import clean_action

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    is_device_tracking = fields.Boolean(default=False, string='Theo dõi thiết bị')
    image_tracking = fields.Image("Hình ảnh xác minh", max_width=1024, max_height=1024)
    stock_receipt_id = fields.Many2one('stock.receipt', string='Phiếu Ghi Nhận', required=False, ondelete='cascade')
    t4tek_stock_picking_type_incoming = fields.Selection([
        ('first_input', 'Nhập lần đầu'),
        ('re_input', 'Tái Nhập'),
        ('warranty_input', 'Nhập để bảo hành'),
        ('fisnish_good_input', 'Nhập thành phẩm'),
    ], string='Loại Nhập')
    t4tek_stock_picking_type_outgoing = fields.Selection([
        ('return_output', 'Xuất trả NCC'),
        ('ware_output', 'Xuất kho khác'),
        ('sale_output', 'Xuất bán'),
        ('warranty_after_output', 'Xuất sau bảo hành')
    ], string='Loại Xuất')
    
    is_loading = fields.Boolean("Loading", default=False)
    
    def action_cancer_scan(self):
        self.is_loading = False
        if self.env.context.get('uuid_client', False):
            self.env['bus.bus'].sudo()._sendone(
                self.env.context.get('uuid_client', False),
                self.env.context.get('uuid_client', False),
                {
                    "type":"cancel_scan",
                    'no_open_popup': True,
                }
            )
    
    def action_generate_cards(self):
        if not self.stock_receipt_id:
            raise ValidationError(_("Phiếu Ghi Nhận Chưa Có."))
        return self.stock_receipt_id.action_generate_cards()
    
    def write(self, vals):
        return super(StockPicking, self).write(vals)
    
    def action_scan_cards_incoming(self):
        if self.env.context.get('uuid_client', False):
            self.env['bus.bus'].sudo()._sendone(
                self.env.context.get('uuid_client', False),
                self.env.context.get('uuid_client', False),
                {
                    "type":"scan_cards",
                    "model": self._name,
                    'receipt_name': "Tạo phiếu nhập kho",
                    'receipt_type': 'incoming',
                    "is_create_auto":True,
                }
            )
        return {'type': 'ir.actions.act_window_close'}
    
    def action_scan_cards(self):
        self.is_loading = True
        if self.env.context.get('uuid_client', False):
            self.env['bus.bus'].sudo()._sendone(
                self.env.context.get('uuid_client', False),
                self.env.context.get('uuid_client', False),
                {
                    "type":"scan_cards",
                    "model": self._name,
                    "id": self.id,
                    'receipt_name': self.picking_type_code == 'incoming' and "Tạo phiếu nhập kho" or "Tạo phiếu xuất kho",
                    'receipt_type': self.picking_type_code,
                    "is_create_auto":False,
                    'no_open_popup': True,
                }
            )
        return {'type': 'ir.actions.act_window_close'}
    
    def action_scan_cards_outgoing(self):
        if self.env.context.get('uuid_client', False):
            self.env['bus.bus'].sudo()._sendone(
                self.env.context.get('uuid_client', False),
                self.env.context.get('uuid_client', False),
                {
                    "type":"scan_cards",
                    "model": self._name,
                    'receipt_name': "Tạo phiếu xuất kho",
                    'receipt_type': 'outgoing',
                    "is_create_auto":True
                }
            )
        return {'type': 'ir.actions.act_window_close'}
    
    def _create_stock_picking_incoming(self):
        """Tạo phiếu kho (stock.picking)"""
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id.company_id', '=', self.env.company.id),
        ], limit=1)
        if not picking_type:
            raise ValidationError("Không tìm thấy loại phiếu kho nhập phù hợp!")
        
        # product_variant = self.product_id.product_variant_ids[0] if self.product_id.product_variant_ids else False
        # if not product_variant:
        #     raise ValidationError(f"Không tìm thấy biến thể sản phẩm cho {self.product_id.name}")
        location_id = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('company_id', '=', self.env.company.id)
        ], limit=1) 
        if not location_id:
            raise ValidationError("Không tìm thấy kho đích phù hợp!")
        picking_vals = {
            'is_device_tracking':True,  # Đánh dấu là phiếu xuất kho thiết bị
            'name': self.env['ir.sequence'].next_by_code('stock.picking') or '/',
            'picking_type_id': picking_type.id,
            'location_dest_id': location_id.id,
            'partner_id': self.env.user.partner_id.id,
            'company_id': self.env.company.id,
            'state': 'draft',
        }
        
        return self.create(picking_vals)
    
    def _create_stock_picking_outgoing(self):
        """Open popup to scan RFID tags for stock issuance from selected cards"""
         # Create stock.picking
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not picking_type:
            raise UserError("Không tìm thấy loại phiếu xuất kho!")
        location_id = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('company_id', '=', self.env.company.id)
        ], limit=1) 
        picking_vals = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': location_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'state': 'draft',
            'partner_id': self.env.user.partner_id.id,
            'company_id': self.env.company.id,
            'is_device_tracking':True,  # Đánh dấu là phiếu xuất kho thiết bị
        })
        return picking_vals

    
    def callback_scan_cards(self, tags, picking_type):
        _logger.info(f"================================={picking_type   }")
        
        
        """Callback function to process scanned RFID tags"""
        if not tags:
            return "Không có thẻ nào được quét!"
        records = []
        if self.picking_type_code == "incoming":
            if self.t4tek_stock_picking_type_incoming == 'first_input':
                for tag in tags:
                    card = self.env['stock.card.line'].search([('card_code', '=', tag['Tid']), ('is_done','=',True)], limit=1)
                    if not card:
                        return f"Thẻ {tag['Tid']} không tồn tại trong hệ thống!"
                    
                    
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
            
            
        
        # Nếu có lỗi trong quá trình scan
        if error_messages:
            return '; '.join(error_messages)
        
        # Nếu không có records nào hợp lệ
        if not records:
            return "Không tìm thấy sản phẩm hợp lệ nào!"
        if self.id == False:

            picking = None
            if picking_type == 'outgoing':
                picking = self._create_stock_picking_outgoing()
            elif picking_type == 'incoming':
                picking = self._create_stock_picking_incoming()
            if picking.picking_type_code == 'outgoing':
                try:
                    # Chuyển đổi list thành recordset
                    card_recordset = self.env['stock.receipt.card'].browse([r.id for r in records])
                    
                    # Gọi method xuất kho
                    result = card_recordset.action_export_cards_v3(
                        picking=picking,
                    )
                    
                    if result != "1":
                        return result
                    
                except Exception as e:
                    return f"Lỗi khi xuất kho: {str(e)}"
            elif picking.picking_type_code == 'incoming':
                try:
                    # Chuyển đổi list thành recordset
                    card_recordset = self.env['stock.receipt.card'].browse([r.id for r in records])
                    
                    # Gọi method xuất kho
                    result = card_recordset.action_import_cards_v3(
                        picking=picking,
                    )
                    if result != "1":
                        return result
                    
                except Exception as e:
                    return f"Lỗi khi xuất kho: {str(e)}"
            return clean_action({'type': 'ir.actions.act_window',
                    'name': _('Phiếu tái nhập kho'if picking.picking_type_code == 'incoming' else 'Phiếu xuất kho'),
                    'res_model': 'stock.picking',
                    'view_mode': 'form',
                    'views': [(False, 'form')],  # ✅ Đúng format: list of tuples
                    "res_id": picking.id,
                    'target': 'current',
                    'context': 
                   {'contact_display': 'partner_address', 'restricted_picking_type_code':  
                        'incoming', 'search_default_reception': 1, 'is_oper':True, 'from_menu':1, 'default_is_device_tracking': True, 'create':0}
                                
                }, self.env)
            
        # Xử lý xuất kho nếu là picking type outgoing
        if self.picking_type_code == 'outgoing':
            try:
                # Chuyển đổi list thành recordset
                card_recordset = self.env['stock.receipt.card'].browse([r.id for r in records])
                
                # Gọi method xuất kho
                result = card_recordset.action_export_cards_v3(
                    picking=self,
                )
                
                return result if result else "1"
                
            except Exception as e:
                return f"Lỗi khi xuất kho: {str(e)}"
        elif self.picking_type_code == 'incoming':
            try:
                # Chuyển đổi list thành recordset
                card_recordset = self.env['stock.receipt.card'].browse([r.id for r in records])
                
                # Gọi method xuất kho
                result = card_recordset.action_import_cards_v3(
                    picking=self,
               
                )
                
                return result if result else "1"
                
            except Exception as e:
                return f"Lỗi khi xuất kho: {str(e)}"
        
        return "1"
    
    # def callback_scan_cards(self, tags, picking_type):
    #     _logger.info(f"================================={tags}")
        
        
    #     """Callback function to process scanned RFID tags"""
    #     if not tags:
    #         return "Không có thẻ nào được quét!"
    #     records = []
       
    #     error_messages = []
        
    #     for tag in tags:
    #         # Kiểm tra tag có đúng format không
    #         if not isinstance(tag, dict) or 'Tid' not in tag:
    #             error_messages.append("Format thẻ không hợp lệ!")
    #             continue
                
    #         # Tìm stock receipt card
    #         card_record = self.env['stock.receipt.card'].search([
    #             ('name', '=', tag['Tid']),
    #         ], limit=1)
            
    #         if not card_record:
    #             error_messages.append(f"Sản phẩm có mã {tag['Tid']} không tồn tại trong hệ thống.")
    #             continue
                
    #         records.append(card_record)
            
            
        
    #     # Nếu có lỗi trong quá trình scan
    #     if error_messages:
    #         return '; '.join(error_messages)
        
    #     # Nếu không có records nào hợp lệ
    #     if not records:
    #         return "Không tìm thấy sản phẩm hợp lệ nào!"
    #     if self.id == False:

    #         picking = None
    #         if picking_type == 'outgoing':
    #             picking = self._create_stock_picking_outgoing()
    #         elif picking_type == 'incoming':
    #             picking = self._create_stock_picking_incoming()
    #         if picking.picking_type_code == 'outgoing':
    #             try:
    #                 # Chuyển đổi list thành recordset
    #                 card_recordset = self.env['stock.receipt.card'].browse([r.id for r in records])
                    
    #                 # Gọi method xuất kho
    #                 result = card_recordset.action_export_cards_v3(
    #                     picking=picking,
    #                 )
                    
    #                 if result != "1":
    #                     return result
                    
    #             except Exception as e:
    #                 return f"Lỗi khi xuất kho: {str(e)}"
    #         elif picking.picking_type_code == 'incoming':
    #             try:
    #                 # Chuyển đổi list thành recordset
    #                 card_recordset = self.env['stock.receipt.card'].browse([r.id for r in records])
                    
    #                 # Gọi method xuất kho
    #                 result = card_recordset.action_import_cards_v3(
    #                     picking=picking,
    #                 )
    #                 if result != "1":
    #                     return result
                    
    #             except Exception as e:
    #                 return f"Lỗi khi xuất kho: {str(e)}"
    #         return clean_action({'type': 'ir.actions.act_window',
    #                 'name': _('Phiếu tái nhập kho'if picking.picking_type_code == 'incoming' else 'Phiếu xuất kho'),
    #                 'res_model': 'stock.picking',
    #                 'view_mode': 'form',
    #                 'views': [(False, 'form')],  # ✅ Đúng format: list of tuples
    #                 "res_id": picking.id,
    #                 'target': 'current',
    #                 'context': 
    #                {'contact_display': 'partner_address', 'restricted_picking_type_code':  
    #                     'incoming', 'search_default_reception': 1, 'is_oper':True, 'from_menu':1, 'default_is_device_tracking': True, 'create':0}
                                
    #             }, self.env)
            
    #     # Xử lý xuất kho nếu là picking type outgoing
    #     if self.picking_type_code == 'outgoing':
    #         try:
    #             # Chuyển đổi list thành recordset
    #             card_recordset = self.env['stock.receipt.card'].browse([r.id for r in records])
                
    #             # Gọi method xuất kho
    #             result = card_recordset.action_export_cards_v3(
    #                 picking=self,
    #             )
                
    #             return result if result else "1"
                
    #         except Exception as e:
    #             return f"Lỗi khi xuất kho: {str(e)}"
    #     elif self.picking_type_code == 'incoming':
    #         try:
    #             # Chuyển đổi list thành recordset
    #             card_recordset = self.env['stock.receipt.card'].browse([r.id for r in records])
                
    #             # Gọi method xuất kho
    #             result = card_recordset.action_import_cards_v3(
    #                 picking=self,
               
    #             )
                
    #             return result if result else "1"
                
    #         except Exception as e:
    #             return f"Lỗi khi xuất kho: {str(e)}"
        
    #     return "1"
    
    
    def callback_scan_cards_outgoing(self, tags):
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
        if self.id == False:
            picking = self._create_stock_picking_incoming()
            if picking.picking_type_code == 'outgoing':
                try:
                    # Chuyển đổi list thành recordset
                    card_recordset = self.env['stock.receipt.card'].browse([r.id for r in records])
                    
                    # Gọi method xuất kho
                    result = card_recordset.action_export_cards_v2(
                        picking=picking,
                        lot_ids=lot_ids
                    )
                    
                    return result if result else "1"
                    
                except Exception as e:
                    return f"Lỗi khi xuất kho: {str(e)}"
            elif picking.picking_type_code == 'incoming':
                try:
                    # Chuyển đổi list thành recordset
                    card_recordset = self.env['stock.receipt.card'].browse([r.id for r in records])
                    
                    # Gọi method xuất kho
                    result = card_recordset.action_import_cards_v2(
                        picking=picking,
                        lot_ids=lot_ids
                    )
                    
                    return result if result else "1"
                    
                except Exception as e:
                    return f"Lỗi khi xuất kho: {str(e)}"
            return {'type': 'ir.actions.act_window',
                    'name': _('Phiếu tái nhập kho'),
                    'res_model': 'stock.picking',
                    'view_mode': 'form',
                    "res_id": picking.id,
                    'target': 'current',
                    'context': 
                   {'contact_display': 'partner_address', 'restricted_picking_type_code':  
                        'incoming', 'search_default_reception': 1, 'is_oper':True, 'from_menu':1, 'default_is_device_tracking': True, 'create':0}
                                
                }
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