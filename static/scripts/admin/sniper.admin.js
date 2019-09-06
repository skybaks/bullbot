'use strict';

$(window).load(function () {
    function getFormData(form) {
        let data = $(form).serializeArray().reduce((obj, item) => {
            obj[item.name] = item.value;
            return obj;
        }, {});

        return data;
    }

    let messageBox = $('#message-box');
    let messageText = $('#message-text');

    $('#message-box-hide-icon').click(() => {
        messageBox.addClass('hidden');
    });

    function resultFeedback(success, text) {
        // reset state...
        messageBox.removeClass('hidden positive negative');

        // then update element.
        if (success) {
            messageBox.addClass('positive');
        } else {
            messageBox.addClass('negative');
        }
        messageText.text(text);
    }

    $('.submission-form').each(function (index, form) {
        console.log(form);
        let formID = $(form).attr('id');

        let acceptButton = $(`button.submission-submit-accept[form="${formID}"]`);
        acceptButton.click(function (event) {
            event.preventDefault();
            let formData = getFormData(form);
            formData['plusone'] = true;
            console.log(formData);

            $.ajax({
                url: `/api/v1/snipers/${encodeURIComponent(formData.username)}`,
                type: 'POST',
                data: JSON.stringify(formData),
                contentType: 'application/json; charset=utf-8',
                success: function (result) {
                    console.log('success result ', result);

                    acceptButton.text('Accept');
                    acceptButton.removeClass('disabled');
                    $.ajax({
                        url: `/api/v1/snipers/${encodeURIComponent(formData.username)}/submit`,
                        type: 'DELETE',
                        data: JSON.stringify(formData),
                        contentType: 'application/json; charset=utf-8',
                        success: function (delresult) {
                            acceptButton.closest("tr").remove();
                            resultFeedback(true, 'Successfully approved submission');
                        }
                    });
                },
                error: function(result) {
                    console.log('error result ', result);

                    acceptButton.text('Accept');
                    acceptButton.removeClass('disabled');
                    resultFeedback(false, 'Failed to approve submission');
                }
            });

            acceptButton.text('Accepting...');
            acceptButton.addClass('disabled');
        });

        let denyButton = $(`button.submission-submit-deny[form="${formID}"]`);
        denyButton.click(function (event) {
            event.preventDefault();
            let formData = getFormData(form);
            console.log(formData);

            $.ajax({
                url: `/api/v1/snipers/${encodeURIComponent(formData.username)}/submit`,
                type: 'DELETE',
                data: JSON.stringify(formData),
                success: function (result) {
                    console.log('success result ', result);

                    location.reload();
                },
                error: function(result) {
                    console.log('error result ', result);

                    denyButton.text('Deny');
                    denyButton.removeClass('disabled');
                    resultFeedback(false, 'Failed to deny submission');
                }
            });

            denyButton.text('Denying...');
            denyButton.addClass('disabled');
        });
    });
});
