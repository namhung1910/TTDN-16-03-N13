odoo.define('cham_cong.face_checkin_widget', function (require) {
    'use strict';

    const AbstractAction = require('web.AbstractAction');
    const core = require('web.core');
    const rpc = require('web.rpc');
    const QWeb = core.qweb;

    // Define template inline
    QWeb.add_template(`
        <templates>
            <t t-name="cham_cong.FaceCheckinWidget">
                <div class="o_face_checkin_widget">
                    <div class="modal-header bg-primary text-white">
                        <h4 class="modal-title">
                            <i class="fa fa-user-circle"/> Điểm Danh Tự Động
                        </h4>
                        <button class="btn btn-sm btn-light o_pause_button" style="margin-left: auto;">
                            <i class="fa fa-pause"/> Tạm dừng
                        </button>
                    </div>
                    
                    <div class="modal-body">
                        <!-- Status Message -->
                        <div class="o_status_container text-center mb-3">
                            <div class="o_status_icon">
                                <i class="fa fa-spinner fa-pulse fa-2x"/>
                            </div>
                            <div class="o_status_text mt-2 h5">
                                <span class="o_status_message">Đang khởi động...</span>
                            </div>
                            <div class="o_status_detail text-muted">
                                <small class="o_status_subtitle"></small>
                            </div>
                        </div>
                        
                        <!-- Camera Container -->
                        <div class="o_camera_container text-center position-relative">
                            <video class="o_camera_video" autoplay="autoplay"/>
                            
                            <!-- Overlay for visual feedback -->
                            <div class="o_camera_overlay d-none">
                                <div class="o_overlay_content">
                                    <i class="fa fa-check-circle fa-4x"/>
                                    <div class="mt-3 h4"></div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Instructions -->
                        <div class="alert alert-info mt-3" role="alert">
                            <strong>💡 Hướng dẫn:</strong>
                            <ul class="mb-0">
                                <li>Đứng vào giữa khung hình</li>
                                <li>Nhìn thẳng vào camera</li>
                                <li>Hệ thống sẽ tự động nhận diện</li>
                                <li>Không cần nhấn nút!</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div class="modal-footer">
                        <div class="o_footer_info text-muted">
                            Độ tin cậy: <span class="o_confidence_display">--</span>%
                        </div>
                        <button class="btn btn-light o_close_button">
                            <i class="fa fa-times"/> Đóng
                        </button>
                    </div>
                </div>
            </t>
        </templates>
    `);

    const FaceCheckinWidget = AbstractAction.extend({
        hasControlPanel: false,
        contentTemplate: 'cham_cong.FaceCheckinWidget',

        events: {
            'click .o_close_button': '_onCloseClick',
            'click .o_pause_button': '_onPauseClick',
        },

        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.action = action;

            // Scanning state
            this.isScanning = false;
            this.isPaused = false;
            this.isProcessing = false;
            this.scanInterval = null;

            // Cooldown management
            this.lastRecognitionTime = 0;
            this.cooldownPeriod = 5000;  // 5 seconds
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

                    // Wait for video to be ready
                    video.onloadedmetadata = function () {
                        self._setStatus('ready', 'Sẵn sàng quét', 'Đứng vào khung hình để bắt đầu');
                        self._startContinuousScanning();
                    };
                })
                .catch(function (error) {
                    self._setStatus('error', 'Lỗi camera', error.message);
                });
        },

        _stopCamera: function () {
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
                this.stream = null;
            }
        },

        _startContinuousScanning: function () {
            const self = this;

            if (this.scanInterval) {
                clearInterval(this.scanInterval);
            }

            this.isScanning = true;
            this.isPaused = false;

            this._setStatus('scanning', 'Đang quét...', 'Tự động phát hiện khuôn mặt');
            this._setBorderState('scanning');

            // Scan every 1 second
            this.scanInterval = setInterval(function () {
                if (!self.isPaused && !self.isProcessing && !self._isInCooldown()) {
                    self._captureAndRecognize();
                }
            }, 1000);
        },

        _stopContinuousScanning: function () {
            if (this.scanInterval) {
                clearInterval(this.scanInterval);
                this.scanInterval = null;
            }
            this.isScanning = false;
            this._setStatus('paused', 'Đã tạm dừng', 'Click để tiếp tục');
            this._setBorderState('idle');
        },

        _isInCooldown: function () {
            const now = Date.now();
            const cooldownRemaining = this.cooldownPeriod - (now - this.lastRecognitionTime);

            if (cooldownRemaining > 0) {
                const secondsLeft = Math.ceil(cooldownRemaining / 1000);
                this._setStatusSubtitle(`Chờ ${secondsLeft}s...`);
                return true;
            }
            return false;
        },

        _captureAndRecognize: async function () {
            const self = this;

            this.isProcessing = true;
            this._setStatus('processing', 'Đang nhận diện...', '');
            this._setBorderState('processing');

            try {
                const imageData = this._captureImage();

                const result = await rpc.query({
                    route: '/api/face/auto_checkin',
                    params: {
                        image_data: imageData
                    }
                });

                await self._handleResult(result);

            } catch (error) {
                self._setStatus('error', 'Lỗi kết nối', error.message || 'Không thể kết nối server');
                self._setBorderState('error');
            } finally {
                this.isProcessing = false;

                // Return to scanning state if still active
                if (this.isScanning && !this.isPaused) {
                    setTimeout(function () {
                        if (!self._isInCooldown()) {
                            self._setStatus('scanning', 'Đang quét...', 'Tự động phát hiện khuôn mặt');
                            self._setBorderState('scanning');
                        }
                    }, 500);
                }
            }
        },

        _handleResult: async function (result) {
            const self = this;

            // Update confidence display
            if (result.data && result.data.confidence) {
                this.$('.o_confidence_display').text(result.data.confidence.toFixed(1));
            }

            if (result.success) {
                // Success!
                this.lastRecognitionTime = Date.now();

                if (result.action === 'checkin') {
                    await this._showSuccess('✅ Check-in thành công!', result.message);
                } else if (result.action === 'checkout') {
                    await this._showSuccess('👋 Check-out thành công!', result.message);
                }

                // NO AUTO-CLOSE - Keep scanning for next person!

            } else {
                // Error or already complete
                const iconClass = result.action === 'already_complete' ? 'fa-check-circle' : 'fa-exclamation-triangle';
                const statusType = result.action === 'already_complete' ? 'info' : 'warning';

                this._setStatus(statusType, result.message, '');
                this._setBorderState(statusType);

                // Continue scanning for other people (NO AUTO-CLOSE)
                this.lastRecognitionTime = Date.now();
            }
        },

        _showSuccess: async function (title, message) {
            // Show success overlay but DON'T stop scanning
            const overlay = this.$('.o_camera_overlay');
            overlay.find('.o_overlay_content .h4').text(title);
            overlay.removeClass('d-none').addClass('o_success');

            this._setStatus('success', message, '');
            this._setBorderState('success');

            // Hide overlay after 2s and resume scanning
            await this._sleep(2000);
            overlay.addClass('d-none').removeClass('o_success');

            // Resume scanning state (not paused!)
            this._setStatus('scanning', 'Đang quét...', 'Tự động phát hiện khuôn mặt');
            this._setBorderState('scanning');
        },



        _captureImage: function () {
            const video = this.$('.o_camera_video')[0];
            const canvas = document.createElement('canvas');

            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;

            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0);

            return canvas.toDataURL('image/jpeg', 0.8);
        },

        _setStatus: function (type, message, subtitle) {
            const $container = this.$('.o_status_container');
            const $icon = $container.find('.o_status_icon i');
            const $message = $container.find('.o_status_message');
            const $subtitle = $container.find('.o_status_subtitle');

            // Icon mapping
            const icons = {
                'ready': 'fa-camera',
                'scanning': 'fa-spinner fa-pulse',
                'processing': 'fa-cog fa-spin',
                'success': 'fa-check-circle text-success',
                'error': 'fa-exclamation-circle text-danger',
                'warning': 'fa-exclamation-triangle text-warning',
                'info': 'fa-info-circle text-info',
                'paused': 'fa-pause-circle text-muted'
            };

            $icon.attr('class', 'fa fa-2x ' + (icons[type] || 'fa-question-circle'));
            $message.text(message);
            $subtitle.text(subtitle || '');
        },

        _setStatusSubtitle: function (text) {
            this.$('.o_status_subtitle').text(text);
        },

        _setBorderState: function (state) {
            const $video = this.$('.o_camera_video');
            $video.removeClass('border-scanning border-processing border-success border-error border-warning border-info border-idle');

            if (state !== 'idle') {
                $video.addClass('border-' + state);
            }
        },

        _onPauseClick: function () {
            if (this.isPaused) {
                // Resume
                this.$('.o_pause_button').html('<i class="fa fa-pause"/> Tạm dừng');
                this._startContinuousScanning();
            } else {
                // Pause
                this.$('.o_pause_button').html('<i class="fa fa-play"/> Tiếp tục');
                this._stopContinuousScanning();
            }
            this.isPaused = !this.isPaused;
        },

        _onCloseClick: function () {
            this.do_action({ type: 'ir.actions.act_window_close' });
        },

        _sleep: function (ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        },

        destroy: function () {
            this._stopContinuousScanning();
            this._stopCamera();

            this._super.apply(this, arguments);
        }
    });

    core.action_registry.add('face_checkin_widget', FaceCheckinWidget);

    return FaceCheckinWidget;
});
