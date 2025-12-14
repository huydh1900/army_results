/** @odoo-module **/

import {registry} from "@web/core/registry";

const digitalSignatureAction = async (env, params) => {

    const action = env.services.action;

    let attachment_id = params.params.attachment_id;
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

        // ---------------------------------------------------
        //   ⚠ CALLBACK PHẢI LÀ async !!!
        // ---------------------------------------------------
        const callback = async (rv) => {
            if (!rv) {
                alert("Không nhận được dữ liệu từ VGCA!");
                return;
            }

            let result;
            try {
                result = JSON.parse(rv);
            } catch (e) {
                alert("Dữ liệu trả về không phải JSON:\n" + rv);
                return;
            }

            if (result.Status === true || result.Status === 0) {

                let originalName = fileData.file_url.split('/').pop();
                let signedName = originalName.replace(/(\.[^.]+)$/, "_signed$1");

                let fileUrl = result.FileServer;
                if (!fileUrl) {
                    alert("VGCA không trả về FileServer!");
                    return;
                }

                // ---------------------------------------------------
                //  ⚠ TẢI FILE ĐÃ KÝ VỀ → CHUYỂN BASE64 (CÓ await)
                // ---------------------------------------------------
                let fileBase64;
                try {
                    const blob = await fetch(fileUrl).then(r => r.blob());
                    fileBase64 = await new Promise((resolve, reject) => {
                        const reader = new FileReader();
                        reader.onloadend = () =>
                            resolve(reader.result.split(",")[1]);
                        reader.onerror = reject;
                        reader.readAsDataURL(blob);
                    });
                } catch (err) {
                    alert("Không thể tải file từ FileServer: " + err);
                    return;
                }

                // ---------------------------------------------------
                //  ⚠ LƯU FILE VÀO ODOO (CÓ await)
                // ---------------------------------------------------
                await env.services.orm.call(
                    "ir.attachment",
                    "mark_signed",
                    [attachment_id, fileBase64, signedName]
                );

                alert("Ký số thành công và file đã được lưu!");

                action.doAction({
                    type: "ir.actions.client",
                    tag: "soft_reload",
                });

            } else {
                alert("Ký thất bại: " + result.Message);
            }
        };

        vgca_sign_approved(JSON.stringify(prms), callback);

    } catch (error) {
        alert("Lỗi hệ thống:\n" + error.message);
    }
};

registry.category("actions").add("digital_signature_action", digitalSignatureAction);
