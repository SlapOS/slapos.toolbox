/*jslint undef: true */
/*global $, document, window, alert, $SCRIPT_ROOT, setInput, ace */
/* vim: set et sts=4: */

$(document).ready(function () {
    "use strict";

    var editor,
        send = false,
        lastli = null,
        partitionAmount = $('input#partitionAmount').val();

    function setupTextarea($txt) {
        var size = Number($txt.attr('id').split('_')[1]),
            hiddenDiv = $(document.createElement('div')),
            content = null;
        hiddenDiv.attr('id', 'div_' + size);
        hiddenDiv.addClass('hiddendiv');
        $('div#parameterkw').append(hiddenDiv);
        $txt.keyup(function () {
            content = $txt.val().replace(/\n/g, '<br>');
            hiddenDiv.html(content);
            if (hiddenDiv.height() > $txt.height() && hiddenDiv.height() > 120) {
                return;
            }
            $txt.css('height', hiddenDiv.height() + 'px');
        });
    }

    function setupFileTree(path) {
        var root = $("input#root").val();
        if (root === '') {
            return;
        }
        if (path) {
            root += '/' + path + '/';
        } else {
            root += '/';
        }
        $('#fileNavigator').gsFileManager({script: $SCRIPT_ROOT + "/fileBrowser", root: root});
    }

    function configRadio() {
        $('#slappart li').each(function () {
            var $radio = $(this).find('input:radio'),
                boxselector = '#box' + $radio.attr('id');

            if ($(this).hasClass('checked')) {
                $(this).removeClass('checked');
                $(boxselector).slideUp('normal');
            }
            if ($radio.is(':checked')) {
                $(this).addClass('checked');
                //change content here
                $(boxselector).slideDown('normal');
            }
        });
    }

    function setupSlappart() {
        var i, elt, fileId;
        for (i = 0; i < partitionAmount; i += 1) {
            elt = $('#slappart' + i + 'Parameter');
            fileId = $('#slappart' + i + 'Files');

            if (elt && elt !== undefined) {
                elt.click(function () {
                    alert($(this).html());
                });
            }
            if (fileId && fileId !== undefined) {
                fileId.click(function () {
                    $('#instancetabfiles').click();
                    setupFileTree($(this).attr('rel'));
                });
            }
        }
    }

    function updateParameter() {
        var xml = '<?xml version="1.0" encoding="utf-8"?>\n',
            software_type = '',
            software_type_input_value = $('input#software_type').val(),
            software_release = $('#software_release').val(),
            size = $('#partitionParameter > tbody > tr').length,
            i;

        if (software_type_input_value !== '' && software_type_input_value !== 'Software Type here...') {
            software_type = software_type_input_value;
        }
        xml += '<instance>\n';
        if (size > 1) {
            // we have to remove the 1st line, which just diplay column names
            for (i = 0; i < size - 1; i += 1) {
                var parameter_name = $("#partitionParameter tr").find("input")[i].value;
                var parameter_value = $("#partitionParameter tr").find("textarea")[i].value;
                if (parameter_name !== '') {
                    xml += '<parameter id="' + parameter_name + '">' + parameter_value + '</parameter>\n';
                }
            }
        }
        xml += '</instance>\n';
        $.ajax({
            type: 'POST',
            url: $SCRIPT_ROOT + '/saveParameterXml',
            data: {
              software_type: software_type,
              software_release: software_release,
              parameter: xml
            },
            success: function (data) {
                if (data.code === 1) {
                    $('#error').Popup('Instance parameters has been updated, please run your instance now!', {type: 'confirm', duration: 5000});
                } else {
                    $('#error').Popup(data.result, {type: 'error', duration: 5000});
                }
            }
        });
    }

    function setupEditor(editable) {
        editor = ace.edit('editorViewer');
        editor.setTheme('ace/theme/crimson_editor');

        editor.getSession().setMode("ace/mode/xml");
        editor.getSession().setTabSize(2);
        editor.getSession().setUseSoftTabs(true);
        editor.renderer.setHScrollBarAlwaysVisible(false);
        if (!editable) {
            editor.setReadOnly(true);
        }
    }

    function loadSoftwareType() {
        $.ajax({
            type: 'GET',
            url: $SCRIPT_ROOT + '/getSoftwareType',
            success: function updateSoftwareType(data) {
                if (data.code === 1 && data.result) {
                    $("#software_type").val(data.result);
                }
            }
        });
    }

    function loadParameter() {
        $.ajax({
            type: 'GET',
            url: $SCRIPT_ROOT + '/getParameterXml/dict',
            success: function (data) {
                var dict, propertie, size;
                if (data.code === 1) {
                    dict = data.result.instance;
                    for (propertie in dict) {
                        $("#add_attribute").click();
                        size = Number($("#partitionParameter > tbody > tr").last().attr('id').split('_')[1]);
                        $("input#txt_" + size).val(propertie);
                        $("textarea#value_" + size).val(dict[propertie]);
                        $("textarea#value_" + size).keyup();
                    }
                } else {
                    $('#error').Popup(data.result, {type: 'error', duration: 5000});
                }
            }
        });
    }

    setupFileTree();
    $($('#slappart li')[0]).find('input:radio').attr('checked', true);
    $('.menu-box-right>div').css('min-height', $('#slappart li').length * 26 + 20 + 'px');
    configRadio();
    $('#slappart li').each(function () {
        lastli = $(this);
        $(this).find('input:radio').change(function () {
            configRadio();
        });
    });
    if (lastli) {
        lastli.css('border-bottom', 'none');
    }

    $('#parameterkw').slideBox('show');
    setupSlappart();
    $('#reloadfiles').click(function () {
        setupFileTree();
    });
    $('#refresh').click(function () {
        if (send) {
            return;
        }
        $('#imgwaitting').fadeIn();
        $.ajax({
            type: 'GET',
            url: $SCRIPT_ROOT + '/supervisordStatus',
            data: '',
            success: function (data) {
                if (data.code === 1) {
                    $('#supervisordcontent').empty();
                    $('#supervisordcontent').append(data.result);
                }
                $('#imgwaitting').fadeOut();
            }
        });
        return false;
    });
    $('#add_attribute').click(function () {
        var size = Number($('#partitionParameter > tbody > tr').last().attr('id').split('_')[1]) + 1,
            row = "<tr id='row_" + size + "'><td class='first'><input type='text' name='txt_" + size + "' id='txt_" + size + "'></td>" +
                "<td style='padding:6px'><textarea class='slap' id='value_" + size + "'></textarea>" +
                "</td><td valign='middle'><span style='margin-left: 10px;' id='btn_" + size + "' class='close'></span></td></tr>";
        $('#partitionParameter').append(row);
        setInput($('input#txt_' + size));
        setupTextarea($('textarea#value_' + size));
        $('#btn_' + size).click(function () {
            var index = $(this).attr('id').split('_')[1];
            $('tr#row_' + index).remove();
        });
        return false;
    });
    $('#updateParameters').click(function () {
        updateParameter();
        return false;
    });
    $('#xmlview').click(function () {
        var content = '<p id="xmllog" class="message"><br/></p>' +
            '<div class="main_content" style="height:230px"><pre id="editorViewer"></pre></div>' +
            '<input type=submit value="Load" id="loadxml" class="button">';
        $.ajax({
            type: 'GET',
            url: $SCRIPT_ROOT + '/getParameterXml/xml',
            success: function (data) {
                if (data.code === 1) {
                    $("#loadxml").unbind('click');
                    $.colorbox.remove();
                    $("#inline_instance").empty();
                    $("#inline_instance").html(content);
                    setupEditor(true);
                    $("a#inlineInstance").colorbox(
                        {
                            inline: true,
                            width: "600px",
                            onComplete: function () {
                                editor.getSession().setValue(data.result);
                            },
                            title: 'INSTANCE PARAMETERS: Load XML file'
                        }
                    );

                    $("a#inlineInstance").click();
                    $("#loadxml").click(function () {
                        //Parse XML file
                        try {
                            var xmlDoc = $.parseXML(editor.getSession().getValue()), $xml = $(xmlDoc);
                            if ($xml.find('parsererror').length !== 0) {
                                $('p#xmllog').html('Error: Invalid XML document!<br/>');
                                return false;
                            }
                        } catch (err) {
                            $('p#xmllog').html('Error: Invalid XML document!<br/>');
                            return false;
                        }
                        $.ajax({
                            type: 'POST',
                            url: $SCRIPT_ROOT + '/saveParameterXml',
                            data: {
                                software_type: '',
                                parameter: editor.getSession().getValue()
                            },
                            success: function (data) {
                                if (data.code === 1) {
                                    window.location.href = $SCRIPT_ROOT + '/inspectInstance#tab3';
                                    window.location.reload();
                                } else {
                                    $('p#xmllog').html(data.result);
                                }
                            }
                        });
                        return false;
                    });
                } else {
                    $('#error').Popup(data.result, {type: 'error', duration: 5000});
                }
            }
        });
    });
    //Load previous instance parameters
    loadParameter();
    loadSoftwareType();
    $('a#parameterTab').click(function () {
        var i,
            size = $('#partitionParameter > tbody > tr').length;
        for (i = 2; i <= size; i += 1) {
            $('textarea#value_' + i).keyup();
        }
    });

    $("#parameter").load($SCRIPT_ROOT + '/getParameterXml');
    $("#update").click(function () {
        if ($("#parameter").val() === '') {
            $("#error").Popup("Can not save empty value!", {type: 'alert', duration: 3000});
        }
        $.ajax({
            type: 'POST',
            url: $SCRIPT_ROOT + '/saveParameterXml',
            data: {parameter: $('#parameter').val().trim()},
            success: function (data) {
                if (data.code === 1) {
                    $('#error').Popup('Instance parameters updated!', {type: 'info', duration: 3000});
                } else {
                    $('#error').Popup(data.result, {type: 'error', duration: 5000});
                }
            }
        });
    });


    function setupBox() {
        var state = $('#softwareType').css('display');
        if (state === 'none') {
            $('#softwareType').slideDown('normal');
            $('#softwareTypeHead').removeClass('hide');
            $('#softwareTypeHead').addClass('show');
        } else {
            $('#softwareType').slideUp('normal');
            $('#softwareTypeHead').removeClass('show');
            $('#softwareTypeHead').addClass('hide');
        }
    }
});
