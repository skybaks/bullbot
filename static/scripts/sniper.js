'use strict';

$(window).load(function () {
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

    $('#submit-kill-form').submit(function (event) {
        event.preventDefault();
        let formData = $(event.target).serializeArray().reduce((obj, item) => {
            obj[item.name] = item.value;
            return obj;
        }, {});

        console.log(formData);

        $.ajax({
            url: `/api/v1/snipers/${encodeURIComponent(formData.username)}/submit`,
            type: 'PUT',
            data: JSON.stringify(formData),
            contentType: 'application/json; charset=utf-8',
            success: function (result) {
                console.log('success result', result);
                resultFeedback(true, "Success");
            },
            error: function(result) {
                console.log('error result', result);
                resultFeedback(false, result.responseJSON);
            },
            complete: function() {
                $("#submit-kill-form").find("input").val("");
            }
        });
    });
});
