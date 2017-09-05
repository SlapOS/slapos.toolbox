/*jslint undef: true */
/*global $, document, window, $SCRIPT_ROOT, ace */
/* vim: set et sts=4: */


$(document).ready(function () {
    "use strict";

    var editor,
        send = false,
        runnerDir = $("input#runnerdir").val();

    function fillContent() {
        $('#fileNavigator').gsFileManager({script: $SCRIPT_ROOT + "/fileBrowser", root: runnerDir});
    }

    $("#reloadfiles").click(function () {
        fillContent();
    });
    fillContent();

    $("#open").click(function () {
        var elt = $("option:selected", $("#softwarelist"));
        if (elt.val() === "No Software Release found") {
            $("#error").Popup("Please select your Software Release", {type: 'alert', duration: 5000});
            return false;
        }
        $.ajax({
            type: "POST",
            url: $SCRIPT_ROOT + '/supplySoftwareRelease',
            data: "path=" + elt.attr('rel'),
            success: function (data) {
                if (data.code === 1) {
                    window.location.href = $SCRIPT_ROOT + '/editSoftwareProfile';
                } else {
                    $("#error").Popup(data.result, {type: 'error', duration: 5000});
                }
            }
        });
        return false;
    });

    $("#delete").click(function () {
        if ($("#softwarelist").val() === "No Software Release found") {
            $("#error").Popup("Please select your Software Release", {type: 'alert', duration: 5000});
            return false;
        }
        if (send) {
            return;
        }
        if (!window.confirm("Do you really want to delete this software release?")) {
            return;
        }
        send = false;
        var elt = $("option:selected", $("#softwarelist"));
        $.ajax({
            type: "POST",
            url: $SCRIPT_ROOT + '/removeSoftwareDir',
            data: {
                md5: $("#softwarelist").val(),
                title: elt.attr('title')
            },
            success: function (data) {
                var i;
                if (data.code === 1) {
                    $("#softwarelist").empty();
                    for (i = 0; i < data.result.length; i += 1) {
                        $("#softwarelist").append('<option value="' + data.result[i].md5 +
                            '" title="' + data.result[i].title + '" rel="' +
                            data.result[i].path + '">' + data.result[i].title + '</option>');
                    }
                    if (data.result.length < 1) {
                        $("#softwarelist").append('<option>No Software Release found</option>');
                        $('#fileTree').empty();
                    }
                    fillContent();
                    $("#error").Popup("Operation complete, Selected Software Release has been delete!",
                                      {type: 'confirm', duration: 5000});
                } else {
                    $("#error").Popup(data.result, {type: 'error'});
                }
                send = false;
            }
        });
        return false;
    });

    function setupEditor() {
        editor = ace.edit("editor");
        editor.setTheme("ace/theme/crimson_editor");

        var CurentMode = require("ace/mode/text").Mode;
        editor.getSession().setMode(new CurentMode());
        editor.getSession().setTabSize(2);
        editor.getSession().setUseSoftTabs(true);
        editor.renderer.setHScrollBarAlwaysVisible(false);
        editor.setReadOnly(true);
    }
});
