/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

// Widget للسيدات
publicWidget.registry.CharityLadiesRegistration = publicWidget.Widget.extend({
    selector: '#ladiesRegistrationForm',
    events: {
        'submit': '_onSubmit',
        'change .file-upload': '_onFileChange',
        'click .remove-file': '_onRemoveFile',
    },

    start() {
        this._super(...arguments);
        console.log('Ladies registration widget initialized');
    },

    _showLoading(show = true) {
        if (show) {
            const loadingDiv = $('<div>', {
                id: 'loadingOverlay',
                class: 'position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center',
                style: 'background: rgba(0,0,0,0.5); z-index: 9999;',
                html: `
                    <div class="bg-white rounded p-4 text-center">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <div>جاري الإرسال...</div>
                    </div>
                `
            });
            $('body').append(loadingDiv);
        } else {
            $('#loadingOverlay').remove();
        }
    },

    _showMessage(type, title, text) {
        this._showLoading(false);

        const alertClass = type === 'error' ? 'alert-danger' : type === 'success' ? 'alert-success' : 'alert-info';
        const alertDiv = $('<div>', {
            class: `alert ${alertClass} alert-dismissible fade show position-fixed top-50 start-50 translate-middle`,
            style: 'z-index: 9999; min-width: 300px;',
            html: `
                <h5 class="alert-heading">${title}</h5>
                <p>${text}</p>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `
        });

        $('body').append(alertDiv);
        setTimeout(() => alertDiv.remove(), 5000);
    },

    _onFileChange(ev) {
        const input = ev.currentTarget;
        const fileId = input.id;
        const previewDiv = this.$(`#${fileId.replace('_file', '_preview')}`);

        if (input.files && input.files[0]) {
            const file = input.files[0];
            const fileName = file.name;
            const fileSize = (file.size / 1024 / 1024).toFixed(2);

            if (parseFloat(fileSize) > 5) {
                this._showMessage('error', 'خطأ', 'حجم الملف يجب أن يكون أقل من 5MB');
                input.value = '';
                return;
            }

            previewDiv.find('.file-name').text(`${fileName} (${fileSize} MB)`);
            previewDiv.show();
            this.$(input).parent().find('.file-upload-info').hide();
        }
    },

    _onRemoveFile(ev) {
        const targetId = this.$(ev.currentTarget).data('target');
        this.$(`#${targetId}`).val('');
        this.$(`#${targetId.replace('_file', '_preview')}`).hide();
        this.$(`#${targetId}`).parent().find('.file-upload-info').show();
    },

    _fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result);
            reader.onerror = error => reject(error);
        });
    },

    async _onSubmit(ev) {
        ev.preventDefault();
        console.log('Form submission started');

        try {
            const formData = new FormData(this.el);
            const data = {};
            const programIds = [];

            // جمع البيانات
            for (let [key, value] of formData.entries()) {
                if (key === 'program_ids') {
                    programIds.push(parseInt(value));
                } else if (!key.endsWith('_file')) {
                    data[key] = value;
                }
            }

            if (programIds.length > 0) {
                data['program_ids'] = JSON.stringify(programIds);
            }

            // إظهار رسالة التحميل
            this._showLoading(true);

            // معالجة الملفات
            const fileFields = ['id_card_file', 'passport_file', 'residence_file'];

            for (const fieldName of fileFields) {
                const fileInput = document.getElementById(fieldName);
                if (fileInput && fileInput.files[0]) {
                    const base64 = await this._fileToBase64(fileInput.files[0]);
                    data[fieldName] = base64.split(',')[1];
                    data[fieldName + '_name'] = fileInput.files[0].name;
                }
            }

            console.log('Sending data to server');

            // إعداد البيانات بصيغة JSON-RPC لـ Odoo
            const jsonRpcData = {
                jsonrpc: "2.0",
                method: "call",
                params: data,
                id: Math.floor(Math.random() * 1000000000)
            };

            // طباعة البيانات للتأكد
            console.log('JSON-RPC Data to be sent:', jsonRpcData);

            // إرسال البيانات باستخدام jQuery AJAX
            $.ajax({
                url: '/registration/submit/ladies',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(jsonRpcData),
                dataType: 'json',
                success: (response) => {
                    console.log('Response received:', response);

                    // التحقق من وجود خطأ في الاستجابة
                    if (response.error) {
                        console.error('Server error:', response.error);
                        this._showMessage('error', 'خطأ', response.error.message || response.error.data?.message || 'حدث خطأ في الخادم');
                        return;
                    }

                    // معالجة النتيجة
                    const result = response.result;
                    this._handleRegistrationResponse(result);
                },
                error: (xhr, status, error) => {
                    console.error('AJAX Error:', error);
                    console.error('Response:', xhr.responseText);

                    // محاولة استخراج رسالة الخطأ
                    let errorMessage = 'حدث خطأ في الاتصال';
                    try {
                        const errorResponse = JSON.parse(xhr.responseText);
                        if (errorResponse.error) {
                            errorMessage = errorResponse.error.message || errorResponse.error.data?.message || errorMessage;
                        }
                    } catch (e) {
                        // ignore JSON parse errors
                    }

                    this._showMessage('error', 'خطأ', errorMessage);
                }
            });

        } catch (error) {
            console.error('Error:', error);
            this._showMessage('error', 'خطأ', error.message || 'حدث خطأ في المعالجة');
        }
    },

    _handleRegistrationResponse(response) {
        this._showLoading(false);

        if (!response.success) {
            this._showMessage('error', 'خطأ', response.error || 'حدث خطأ في الحجز');
            return;
        }

        // عضوة موجودة مع اشتراك نشط
        if (response.member_found && response.active_subscription?.has_active_subscription) {
            const subscription = response.active_subscription;

            if (confirm(`مرحباً ${response.member_name}!\n\nلديك اشتراك نشط ينتهي في ${subscription.end_date}\nهل تريدين الاستمرار؟`)) {
                this._redirectAfterSuccess(response);
            } else {
                window.location.reload();
            }
        }
        // عضوة موجودة بدون اشتراك نشط
        else if (response.member_found) {
            this._showMessage('info', 'تم العثور على ملفك', `مرحباً ${response.member_name}!`);
            setTimeout(() => {
                this._redirectAfterSuccess(response);
            }, 2000);
        }
        // عضوة جديدة
        else {
            this._showMessage('success', 'تم التسجيل بنجاح', 'سيتم توجيهك الآن...');
            setTimeout(() => {
                this._redirectAfterSuccess(response);
            }, 1500);
        }
    },

    _redirectAfterSuccess(response) {
        if (response.has_invoice && response.invoice) {
            window.location.href = `/registration/invoice/${response.invoice.invoice_id}/${response.invoice.access_token}`;
        } else {
            window.location.href = `/registration/success/ladies/${response.booking_id}`;
        }
    }
});

// Widget للنوادي
publicWidget.registry.CharityClubRegistration = publicWidget.Widget.extend({
    selector: '#clubRegistrationForm',
    events: {
        'submit': '_onSubmit',
        'change #hasHealth': '_onHealthChange',
    },

    start() {
        this._super(...arguments);
        console.log('Club registration widget initialized');
    },

    _onHealthChange(ev) {
        const $checkbox = this.$(ev.currentTarget);
        const $healthDetails = this.$('#healthDetails');

        if ($checkbox.is(':checked')) {
            $healthDetails.slideDown();
        } else {
            $healthDetails.slideUp();
        }
    },

    _showLoading(show = true) {
        if (show) {
            const loadingDiv = $('<div>', {
                id: 'loadingOverlay',
                class: 'position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center',
                style: 'background: rgba(0,0,0,0.5); z-index: 9999;',
                html: `
                    <div class="bg-white rounded p-4 text-center">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <div>جاري الإرسال...</div>
                    </div>
                `
            });
            $('body').append(loadingDiv);
        } else {
            $('#loadingOverlay').remove();
        }
    },

    _showMessage(type, title, text) {
        this._showLoading(false);

        const alertClass = type === 'error' ? 'alert-danger' : 'alert-success';
        const alertDiv = $('<div>', {
            class: `alert ${alertClass} alert-dismissible fade show position-fixed top-50 start-50 translate-middle`,
            style: 'z-index: 9999; min-width: 300px;',
            html: `
                <h5 class="alert-heading">${title}</h5>
                <p>${text}</p>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `
        });

        $('body').append(alertDiv);
        setTimeout(() => alertDiv.remove(), 5000);
    },

    _onSubmit(ev) {
        ev.preventDefault();

        const formData = this.$el.serializeArray();
        const data = {};

        formData.forEach((field) => {
            data[field.name] = field.value;
        });

        this._showLoading(true);

        // إعداد البيانات بصيغة JSON-RPC لـ Odoo
        const jsonRpcData = {
            jsonrpc: "2.0",
            method: "call",
            params: data,
            id: Math.floor(Math.random() * 1000000000)
        };

        // إرسال البيانات باستخدام jQuery AJAX
        $.ajax({
            url: '/registration/submit/club',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(jsonRpcData),
            dataType: 'json',
            success: (response) => {
                if (response.error) {
                    this._showMessage('error', 'خطأ', response.error.message || response.error.data?.message || 'حدث خطأ');
                    return;
                }

                const result = response.result;
                if (result.success) {
                    this._showMessage('success', 'تم التسجيل بنجاح', 'سيتم توجيهك الآن...');
                    setTimeout(() => {
                        window.location.href = `/registration/success/club/${result.registration_id}`;
                    }, 1500);
                } else {
                    this._showMessage('error', 'خطأ', result.error || 'حدث خطأ في التسجيل');
                }
            },
            error: (xhr, status, error) => {
                console.error('Error:', error);
                this._showMessage('error', 'خطأ', 'حدث خطأ في الاتصال');
            }
        });
    }
});

// Widget للدفع
publicWidget.registry.CharityPaymentProcess = publicWidget.Widget.extend({
    selector: '#processPayment',
    events: {
        'click': '_onProcessPayment',
    },

    _showLoading(show = true) {
        if (show) {
            const loadingDiv = $('<div>', {
                id: 'loadingOverlay',
                class: 'position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center',
                style: 'background: rgba(0,0,0,0.5); z-index: 9999;',
                html: `
                    <div class="bg-white rounded p-4 text-center">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <div>جاري معالجة الدفعة...</div>
                    </div>
                `
            });
            $('body').append(loadingDiv);
        } else {
            $('#loadingOverlay').remove();
        }
    },

    _showMessage(type, title, text) {
        this._showLoading(false);

        const alertClass = type === 'error' ? 'alert-danger' : type === 'warning' ? 'alert-warning' : 'alert-success';
        const alertDiv = $('<div>', {
            class: `alert ${alertClass} alert-dismissible fade show position-fixed top-50 start-50 translate-middle`,
            style: 'z-index: 9999; min-width: 300px;',
            html: `
                <h5 class="alert-heading">${title}</h5>
                <p>${text}</p>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `
        });

        $('body').append(alertDiv);
        setTimeout(() => alertDiv.remove(), 5000);
    },

    _onProcessPayment(ev) {
        const selectedProvider = $('input[name="payment_provider"]:checked');

        if (!selectedProvider.length) {
            this._showMessage('warning', 'تنبيه', 'يرجى اختيار طريقة الدفع');
            return;
        }

        const providerId = selectedProvider.val();
        const providerCode = selectedProvider.data('provider-code');
        const invoiceId = this.$el.data('invoice-id');
        const accessToken = this.$el.data('access-token');

        this._showLoading(true);

        // إنشاء معاملة الدفع
        const jsonRpcData = {
            jsonrpc: "2.0",
            method: "call",
            params: {
                invoice_id: invoiceId,
                access_token: accessToken,
                provider_id: providerId
            },
            id: Math.floor(Math.random() * 1000000000)
        };

        $.ajax({
            url: '/registration/payment/transaction/' + invoiceId + '/' + accessToken,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(jsonRpcData),
            dataType: 'json',
            success: (response) => {
                this._showLoading(false);

                if (response.error) {
                    this._showMessage('error', 'خطأ', response.error.message || response.error.data?.message || 'حدث خطأ');
                    return;
                }

                const result = response.result;
                if (result.success) {
                    // معالجة حسب نوع مزود الدفع
                    if (providerCode === 'demo') {
                        // للدفع التجريبي، ننتقل مباشرة للنجاح
                        this._processTestPayment(result.transaction_id);
                    } else if (result.payment_link) {
                        // للمزودين الآخرين، نفتح رابط الدفع
                        window.location.href = result.payment_link;
                    } else {
                        // معالجة مخصصة حسب المزود
                        this._processProviderPayment(providerCode, result);
                    }
                } else {
                    this._showMessage('error', 'خطأ', result.error || 'فشل إنشاء معاملة الدفع');
                }
            },
            error: (xhr, status, error) => {
                console.error('Payment error:', error);
                this._showLoading(false);
                this._showMessage('error', 'خطأ', 'حدث خطأ في الاتصال');
            }
        });
    },

    _processTestPayment(transactionId) {
        // محاكاة عملية الدفع التجريبي
        this._showMessage('info', 'دفع تجريبي', 'جاري محاكاة عملية الدفع...');

        setTimeout(() => {
            this._checkPaymentStatus(transactionId);
        }, 2000);
    },

    _processProviderPayment(providerCode, result) {
        // يمكن إضافة معالجة مخصصة لكل مزود
        console.log('Processing payment for provider:', providerCode, result);

        // افتراضياً، نتحقق من حالة المعاملة
        if (result.transaction_id) {
            this._checkPaymentStatus(result.transaction_id);
        }
    },

    _checkPaymentStatus(transactionId) {
        const jsonRpcData = {
            jsonrpc: "2.0",
            method: "call",
            params: {
                transaction_id: transactionId
            },
            id: Math.floor(Math.random() * 1000000000)
        };

        $.ajax({
            url: '/registration/payment/status/' + transactionId,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(jsonRpcData),
            dataType: 'json',
            success: (response) => {
                if (response.error) {
                    this._showMessage('error', 'خطأ', response.error.message || 'حدث خطأ');
                    return;
                }

                const result = response.result;
                if (result.success && result.state === 'done') {
                    this._showMessage('success', 'تم الدفع بنجاح!', result.message);
                    setTimeout(() => {
                        window.location.href = result.redirect_url;
                    }, 1500);
                } else if (result.state === 'pending') {
                    // إعادة المحاولة بعد فترة
                    setTimeout(() => {
                        this._checkPaymentStatus(transactionId);
                    }, 3000);
                } else {
                    this._showMessage('error', 'فشل الدفع', result.message || 'لم تكتمل عملية الدفع');
                }
            },
            error: (xhr, status, error) => {
                console.error('Status check error:', error);
                this._showMessage('error', 'خطأ', 'حدث خطأ في التحقق من حالة الدفع');
            }
        });
    }
});

console.log('Charity registration widgets loaded');