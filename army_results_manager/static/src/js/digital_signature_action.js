/** @odoo-module **/

import {registry} from "@web/core/registry";

const digitalSignatureAction = async (env, params) => {

    console.log("JS chạy với params:", params);
    const action = env.services.action;

    let attachment_id = params.params.attachment_id
    try {
        const fileData = await env.services.orm.call(
            "ir.attachment",
            "vgca_sign_msg",
            [attachment_id]
        );

        if (fileData.error) {
            alert("Xảy ra lỗi: " + fileData.error);
            return;
        }

        if (typeof vgca_sign_approved === "undefined") {
            alert("VGCA Plugin chưa được load!");
            return;
        }

        const prms = {
            FileUploadHandler: fileData.upload_handler,
            SessionId: fileData.session_id || "",
            FileName: fileData.file_url,
        };

        const callback = (rv) => {
            if (!rv) {
                alert("Không nhận được dữ liệu từ VGCA!");
                return;
            }

            let result;
            try {
                result = JSON.parse(rv);
                console.log(result)
            } catch (e) {
                alert("Dữ liệu trả về không phải JSON:\n" + rv);
                return;
            }

            if (result.Status === true || result.Status === 0) {
                let attachment_id = params.params.attachment_id;
                env.services.orm.call("ir.attachment", "mark_signed", [attachment_id])
                let localPath = result.LocalPath || result.SavePath || "";
                let finalName = result.FileName || "";

                // Hiển thị thông tin đầy đủ cho người dùng
                alert(
                    "File đã ký thành công!\n\n" +
                    "Tên file: " + finalName + "\n" +
                    "Đã lưu tại: " + localPath + "\n\n" +
                    "Bạn có thể mở file để kiểm tra."
                );
                action.doAction({
                    'type': 'ir.actions.client',
                    'tag': 'soft_reload',
                });
                window.open(result.FileServer, "_blank");
            } else {
                alert("Ký số thất bại!\n" + result.Message);
            }
        };

        vgca_sign_approved(JSON.stringify(prms), callback);

    } catch (error) {
        alert("Lỗi hệ thống:\n" + error.message);
    }

};

const actionRegistry = registry.category("actions");
actionRegistry.add("digital_signature_action", digitalSignatureAction);
