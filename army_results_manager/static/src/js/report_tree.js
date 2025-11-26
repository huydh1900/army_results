/** @odoo-module */
import {ListController} from "@web/views/list/list_controller";
import {registry} from '@web/core/registry';
import {listView} from '@web/views/list/list_view';
import {useService} from "@web/core/utils/hooks";

export class ReportListController extends ListController {
    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    OnOpenWizard() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'print.word.wizard',
            name: 'In Báo cáo',
            view_mode: "form",
            target: "new",
            views: [[false, "form"]],
        });
    }

    async signDocument() {
        try {
            console.log('=== BẮT ĐẦU QUÁ TRÌNH KÝ FILE ===');

            // Bước 1: Lấy thông tin file và hash
            console.log('Bước 1: Lấy thông tin file...');
            const fileData = await this.orm.call(
                "training.day",
                "vgca_sign_msg",
                []
            );

            console.log('✅ File data:', fileData);
            console.log('- File name:', fileData.file_name);
            console.log('- File URL:', fileData.file_url);
            console.log('- Hash value:', fileData.hash_value);
            console.log('- JSON data:', fileData.json_data);

            if (fileData.error) {
                alert(fileData.error);
                return;
            }

            // Bước 2: Kiểm tra VGCA
            if (typeof vgca_sign_msg === 'undefined') {
                alert('VGCA Plugin chưa sẵn sàng.\n\n' +
                    'Vui lòng đảm bảo:\n' +
                    '1. VGCA Plugin đã cài đặt\n' +
                    '2. VGCA Service đang chạy\n' +
                    '3. USB Token đã cắm\n' +
                    '4. Đã tải lại trang');
                return;
            }

            // Bước 3: Chuẩn bị parameters
            const prms = {
                "HashValue": fileData.hash_value,
                "HashAlg": "SHA256"
            };

            console.log('=== PARAMETERS ===');
            console.log('HashValue:', prms.HashValue);
            console.log('HashAlg:', prms.HashAlg);
            console.log('Full params:', JSON.stringify(prms, null, 2));

            // Bước 4: Gọi VGCA ký
            console.log('Bước 2: Gọi VGCA Plugin để ký...');
            const sender = `sign_file_${fileData.attachment_id}`;

            vgca_sign_msg(sender, prms, (senderCallback, evData) => {
                console.log('=== NHẬN KẾT QUẢ TỪ VGCA ===');
                this.handleSignResult(senderCallback, evData, fileData);
            });

        } catch (error) {
            console.error('❌ Exception:', error);
            console.error('Stack:', error.stack);
            alert('Có lỗi xảy ra: ' + error.message);
        }
    }

    handleSignResult(sender, evData, fileData) {
        console.log('=== KẾT QUẢ KÝ ===');
        console.log('Sender:', sender);
        console.log('Event Data:', evData);
        console.log('Status:', evData?.Status);
        console.log('Message:', evData?.Message);
        console.log('HashValue:', evData?.HashValue);
        console.log('Signature preview:', evData?.Signature?.substring(0, 100));

        if (evData.Status === 0) {
            console.log('✅ KÝ THÀNH CÔNG!');

            if (evData.Signature && evData.Signature.length > 0) {
                console.log('Signature length:', evData.Signature.length);
                this.saveSignature(fileData.attachment_id, evData.Signature, fileData.json_data);
            } else {
                console.error('❌ Không có chữ ký trong response');
                alert('Lỗi: VGCA không trả về chữ ký');
            }
        } else {
            console.error('❌ KÝ THẤT BẠI');
            this.handleSignError(evData);
        }
    }

    handleSignError(evData) {
        const statusCode = evData.Status;
        const message = evData.Message || 'Không có thông báo lỗi';

        console.error('Error Status:', statusCode);
        console.error('Error Message:', message);
        console.error('Error Hex:', '0x' + statusCode.toString(16).toUpperCase());

        let errorMsg = `❌ Ký thất bại!\n\n`;
        errorMsg += `Mã lỗi: ${statusCode} (0x${statusCode.toString(16).toUpperCase()})\n\n`;

        // Giải thích lỗi phổ biến
        switch (statusCode) {
            case 1:
                errorMsg += '📌 Người dùng đã hủy thao tác';
                break;
            case 2:
                errorMsg += '📌 Không tìm thấy USB Token\n\n';
                errorMsg += 'Kiểm tra:\n';
                errorMsg += '• USB Token đã được cắm?\n';
                errorMsg += '• Driver đã được cài đặt?';
                break;
            case 3:
                errorMsg += '📌 Sai PIN hoặc Token bị khóa\n\n';
                errorMsg += '• Nhập lại PIN\n';
                errorMsg += '• Nếu nhập sai 3 lần, token sẽ bị khóa';
                break;
            case 4:
                errorMsg += '📌 Không tìm thấy chứng thư số hợp lệ\n\n';
                errorMsg += '• Kiểm tra chứng thư đã được import?\n';
                errorMsg += '• Chứng thư còn hiệu lực?';
                break;
            case 19: // 0x8019
                errorMsg += '📌 Dữ liệu không hợp lệ\n\n';
                errorMsg += 'Có thể do:\n';
                errorMsg += '• File URL không truy cập được\n';
                errorMsg += '• JSON structure không đúng format\n';
                errorMsg += '• Thiếu trường bắt buộc\n\n';
                errorMsg += `Chi tiết: ${message}`;
                break;
            default:
                errorMsg += `📌 ${message}`;
        }

        alert(errorMsg);
    }

    async saveSignature(attachmentId, signature, jsonData) {
        try {
            console.log('=== LƯU CHỮ KÝ ===');
            console.log('Attachment ID:', attachmentId);
            console.log('Signature length:', signature.length);
            console.log('JSON data length:', jsonData.length);

            const result = await this.orm.call(
                "training.day",
                "save_signature",
                [attachmentId, signature, jsonData]
            );

            if (result.success) {
                console.log('✅ ĐÃ LƯU THÀNH CÔNG!');
                alert('✅ Ký số thành công!\n\n' +
                    'Chữ ký đã được lưu vào hệ thống.\n' +
                    'File đã ký có thể tải về từ attachments.');

                // Reload để hiển thị file đã ký
                window.location.reload();
            } else {
                throw new Error(result.error || 'Không lưu được chữ ký');
            }

        } catch (error) {
            console.error('❌ Lỗi lưu chữ ký:', error);
            alert('Lỗi khi lưu chữ ký vào database:\n' + error.message);
        }
    }

    reload() {
        // Reload lại view hoặc form
        window.location.reload();
    }
}

registry.category("views").add("button_in_tree", {
    ...listView,
    Controller: ReportListController,
    buttonTemplate: "button_report.ListView.Buttons",
});