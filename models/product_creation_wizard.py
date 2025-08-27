# models/product_creation_wizard.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProductCreationWizard(models.Model):
    _name = 'product.creation.wizard'
    _description = 'Model để tạo sản phẩm mới với tracking serial'
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Tên Sản Phẩm', 
        required=True,
        help='Nhập tên sản phẩm mới'
    )
    
    component_ids = fields.Many2many(
        'product.template',
        'product_creation_wizard_component_rel',
        'wizard_id',
        'component_id',
        string='Nguyên Vật Liệu',
        help='Chọn các nguyên vật liệu của thành phẩm'
    )
    
    # Thêm các trường để theo dõi
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('created', 'Đã Tạo'),
    ], string='Trạng Thái', default='draft', tracking=True)
    
    product_id = fields.Many2one(
        'product.template',
        string='Sản Phẩm Đã Tạo',
        readonly=True,
        help='Sản phẩm được tạo từ wizard này'
    )
    
    create_date = fields.Datetime(string='Ngày Tạo', readonly=True)
    create_uid = fields.Many2one('res.users', string='Người Tạo', readonly=True)

    @api.constrains('component_ids')
    def _check_component_ids(self):
        """Kiểm tra ít nhất có 1 sản phẩm con được chọn"""
        for record in self:
            if not record.component_ids:
                raise ValidationError('Vui lòng chọn ít nhất một sản phẩm con!')

    def action_print(self):
        pass
    def action_create_product(self):
        """Tạo sản phẩm mới với các thông tin đã nhập"""
        self.ensure_one()
        
        # Kiểm tra đã tạo sản phẩm chưa
        if self.state == 'created':
            return {
                'type': 'ir.actions.act_window',
                'name': f'Sản phẩm: {self.product_id.name}',
                'res_model': 'product.template',
                'res_id': self.product_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        
        # Tạo product.template mới
        product_vals = {
            'name': self.name,
            'is_storable': 'product',  # Sản phẩm có thể lưu trữ
            'tracking': 'serial',  # Tracking theo serial number
        }
        
        # Tạo sản phẩm
        new_product = self.env['product.template'].create(product_vals)
        
        # Cập nhật wizard
        self.write({
            'state': 'created',
            'product_id': new_product.id,
        })
        
        # Hiển thị thông báo thành công và chuyển đến sản phẩm vừa tạo
        return {
            'type': 'ir.actions.act_window',
            'name': f'Sản phẩm: {new_product.name}',
            'res_model': 'product.template',
            'res_id': new_product.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        """Hủy bỏ việc tạo sản phẩm"""
        return {'type': 'ir.actions.act_window_close'}
    
    def action_view_product(self):
        """Xem sản phẩm đã tạo"""
        self.ensure_one()
        if self.product_id:
            return {
                'type': 'ir.actions.act_window',
                'name': f'Sản phẩm: {self.product_id.name}',
                'res_model': 'product.template',
                'res_id': self.product_id.id,
                'view_mode': 'form',
                'target': 'current',
            }