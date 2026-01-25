odoo.define('cham_cong.face_camera_widget', function (require) {
    'use strict';

    const AbstractAction = require('web.AbstractAction');
    const core = require('web.core');
    const rpc = require('web.rpc');
    const QWeb = core.qweb;

    // Define template inline
    QWeb.add_template(`
        <templates>
            <t t-name="cham_cong.FaceCameraWidget">
                <div class="o_face_camera_widget">
                    <div class="modal-header">
                        <h4 class="modal-title">
                            <i class="fa fa-camera"/> Đăng Ký Khuôn Mặt
                        </h4>
                    </div>
                    
                    <div class="modal-body">
                        <div class="alert d-none o_message_alert" role="alert">
                            <span class="o_message_text"/>
                        </div>
                        
                        <div class="o_camera_container text-center">
                            <video class="o_camera_video" autoplay="autoplay"/>
                            <img class="o_camera_preview" style="display:none;"/>
                        </div>
                        
                        <div class="alert alert-info mt-3" role="alert">
                            <strong>📸 Hướng dẫn:</strong>
                            <ul class="mb-0">
                                <li>Đặt mặt vào giữa khung hình</li>
                                <li>Nhìn thẳng vào camera</li>
                                <li>Đảm bảo ánh sáng đủ</li>
                                <li>Không đeo khẩu trang/kính</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div class="modal-footer">
                        <button class="btn btn-primary o_capture_button">
                            <i class="fa fa-camera"/> Chụp Ảnh
                        </button>
                        
                        <button class="btn btn-secondary o_retake_button" style="display:none;">
                            <i class="fa fa-undo"/> Chụp Lại
                        </button>
                        
                        <button class="btn btn-success o_register_button" disabled="disabled">
                            <i class="fa fa-check"/> Đăng Ký
                        </button>
                        
                        <button class="btn btn-light o_cancel_button">
                            <i class="fa fa-times"/> Hủy
                        </button>
                    </div>
                </div>
            </t>
        </templates>
    `);

    const FaceCameraWidget = AbstractAction.extend({
        hasControlPanel: false,
        contentTemplate: 'cham_cong.FaceCameraWidget',

        events: {
            'click .o_capture_button': '_onCaptureClick',
            'click .o_register_button': '_onRegisterClick',
            'click .o_retake_button': '_onRetakeClick',
            'click .o_cancel_button': '_onCancelClick',
        },

        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.action = action;
            this.capturedImage = null;
            this.processing = false;
            this.message = null;
            this.messageType = null;
        },

        start: function () {
            const self = this;
            return this._super.apply(this, arguments).then(function () {
                self._startCamera();
            });
        },

        _startCamera: function () {
            const self = this;
            const video = this.$('.o_camera_video')[0];

            const constraints = {
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                }
            };

            navigator.mediaDevices.getUserMedia(constraints)
                .then(function (stream) {
                    video.srcObject = stream;
                    self.stream = stream;
                })
                .catch(function (error) {
                    self._showMessage('Không thể truy cập camera: ' + error.message, 'danger');
                });
        },

        _stopCamera: function () {
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
                this.stream = null;
            }
        },

        _onCaptureClick: function () {
            const video = this.$('.o_camera_video')[0];
            const canvas = document.createElement('canvas');

            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;

            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0);

            // Convert to base64
            this.capturedImage = canvas.toDataURL('image/jpeg', 0.8);

            // Show preview
            this.$('.o_camera_preview').attr('src', this.capturedImage).show();
            this.$('.o_camera_video').hide();
            this.$('.o_register_button').prop('disabled', false);
            this.$('.o_retake_button').show();
            this.$('.o_capture_button').hide();

            this._showMessage('Ảnh đã được chụp! Nhấn "Đăng Ký" để hoàn tất.', 'info');
        },

        _onRetakeClick: function () {
            this.capturedImage = null;
            this.$('.o_camera_preview').hide();
            this.$('.o_camera_video').show();
            this.$('.o_register_button').prop('disabled', true);
            this.$('.o_retake_button').hide();
            this.$('.o_capture_button').show();
            this._showMessage(null, null);
        },

        _onRegisterClick: function () {
            const self = this;

            if (!this.capturedImage) {
                this._showMessage('Vui lòng chụp ảnh trước!', 'warning');
                return;
            }

            this.processing = true;
            this.$('.o_register_button').prop('disabled', true);
            this._showMessage('Đang xử lý...', 'info');

            const nhanVienId = this.action.context.active_id;

            rpc.query({
                route: '/api/face/register',
                params: {
                    nhan_vien_id: nhanVienId,
                    image_data: this.capturedImage
                }
            }).then(function (result) {
                if (result.success) {
                    // Use displayNotification instead of do_notify
                    self.displayNotification({
                        title: 'Thành công',
                        message: result.message,
                        type: 'success'
                    });
                    self.do_action({ type: 'ir.actions.act_window_close' });
                    // Reload parent view
                    self.trigger_up('reload');
                } else {
                    self._showMessage(result.message, 'danger');
                }
            }).catch(function (error) {
                self._showMessage('Lỗi: ' + (error.message.message || error.message), 'danger');
            }).finally(function () {
                self.processing = false;
                self.$('.o_register_button').prop('disabled', false);
            });
        },

        _onCancelClick: function () {
            this.do_action({ type: 'ir.actions.act_window_close' });
        },

        _showMessage: function (message, type) {
            this.message = message;
            this.messageType = type;

            const $alert = this.$('.o_message_alert');
            if (message) {
                $alert.removeClass('d-none alert-info alert-warning alert-danger alert-success');
                $alert.addClass('alert-' + type);
                $alert.find('.o_message_text').text(message);
            } else {
                $alert.addClass('d-none');
            }
        },

        destroy: function () {
            this._stopCamera();
            this._super.apply(this, arguments);
        }
    });

    core.action_registry.add('face_camera_widget', FaceCameraWidget);

    return FaceCameraWidget;
});
