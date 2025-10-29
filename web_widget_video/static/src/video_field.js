/** @odoo-module **/

import {registry} from '@web/core/registry';
import {url} from '@web/core/utils/urls';
import {BinaryField} from '@web/views/fields/binary/binary_field';
import {isBinarySize} from '@web/core/utils/binary';

function base64ToBlob(base64String, contentType) {
    const byteCharacters = atob(base64String);
    const byteArrays = [];

    for (let offset = 0; offset < byteCharacters.length; offset += 1024) {
        const slice = byteCharacters.slice(offset, offset + 1024);

        const byteNumbers = new Array(slice.length);
        for (let i = 0; i < slice.length; i++) {
            byteNumbers[i] = slice.charCodeAt(i);
        }

        const byteArray = new Uint8Array(byteNumbers);
        byteArrays.push(byteArray);
    }

    return new Blob(byteArrays, {type: contentType});
}

export class VideoField extends BinaryField {

    get url() {
        if (isBinarySize(this.props.value)) {
            return url('/web/content', {
                model: this.props.record.resModel,
                id: this.props.record.resId,
                field: this.props.name,
            })
        }

        const base64String = this.props.record.data[this.props.name];
        const contentType = 'video/mp4';
        const videoBlob = base64ToBlob(base64String, contentType);
        return URL.createObjectURL(videoBlob);
    }

}

VideoField.template = 'web_widget_video.VideoField';
VideoField.defaultProps = {
    acceptedFileExtensions: 'video/*',
};

registry.category('fields').add('video', VideoField);
