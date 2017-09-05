/*jslint undef: true */
/*global $, document, window, $SCRIPT_ROOT */
/* vim: set et sts=4: */

$(document).ready(function () {
    "use strict";

    var method = $("input#method").val(),
        workdir = $("input#workdir").val();

    function checkFolder(path) {
        $.ajax({
            type: "POST",
            url: $SCRIPT_ROOT + '/checkFolder',
            data: "path=" + path,
            success: function (data) {
                var path = data.result;
                $("input#path").val(path);
                if (path !== "") {
                    $("#check").fadeIn('normal');
                } else {
                    $("#check").hide();
                }
            }
        });
        return "";
    }

    function selectFile(file) {
        $("#info").empty();
        $("input#subfolder").val(file);
        if (method === "open") {
            $("#info").append("Selection: " + file);
            checkFolder(file);
        } else {
            if ($("input#software").val() !== "" && $("input#software").val().match(/^[\w\d._\-]+$/)) {
                $("#info").append("New Software in: " + file + $("input#software").val());
            } else {
                $("#info").append("Selection: " + file);
            }
        }
        return;
    }

    function initTree(tree, path, key){
      if (!key){
        key = '0';
      }
      $(tree).fancytree({
        activate: function(event, data) {
          var node = data.node;
        },
        click: function(event, data) {
          selectFile(data.node.data.path +"/");
        },
        source: {
          url: $SCRIPT_ROOT + "/fileBrowser",
          data:{opt: 20, dir: path, key: key, listfiles: ''},
          cache: false
        },
        lazyload: function(event, data) {
          var node = data.node;
          data.result = {
            url: $SCRIPT_ROOT + "/fileBrowser",
            data: {opt: 20, dir: node.data.path , key: node.key, listfiles: ''}
          }
        },
      });
    }

    if (method !== "file") {
        initTree('#fileTree', workdir);
    }
    $("input#subfolder").val("");
    $("#create").click(function () {
        if ($("input#software").val() === "" || !$("input#software").val().match(/^[\w\d._\-]+$/)) {
            $("#error").Popup("Invalid Software name", {type: 'alert', duration: 3000});
            return false;
        }
        if ($("input#subfolder").val() === "") {
            $("#error").Popup("Select the parent folder of your software!", {type: 'alert', duration: 3000});
            return false;
        }
        $.ajax({
            type: "POST",
            url: $SCRIPT_ROOT + '/createSoftware',
            data: "folder=" + $("input#subfolder").val() + $("input#software").val(),
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

    $("#open").click(function () {
        $("#flash").fadeOut('normal');
        $("#flash").empty();
        $("#flash").fadeIn('normal');
        if ($("input#path").val() === "") {
            $("#error").Popup("Select a valid Software Release folder!", {type: 'alert', duration: 3000});
            return false;
        }
        $.ajax({
            type: "POST",
            url: $SCRIPT_ROOT + '/supplySoftwareRelease',
            data: "path=" + $("input#path").val(),
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
});
