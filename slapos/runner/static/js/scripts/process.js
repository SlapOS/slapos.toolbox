/*jslint undef: true */
/*global $, window, $SCRIPT_ROOT, setRunningState, setCookie, getCookie, deleteCookie */
/*global currentState: true, running: false, $current: true, currentProcess: true, processTypes: true */
/*global sendStop: true, openedlogpage: true, logReadingPosition: true, speed: true */
/*global isRunning: true */
/* vim: set et sts=4: */

//Global Traitment!!!

var currentState = false;
var running = false;
var currentProcess = "";
var processTypes = {instance:"instance", software:"software"};
var sendStop = false;
var forcedStop = false;
var openedlogpage = ""; //content software or instance if the current page is software or instance log, otherwise nothing
var logReadingPosition = 0;
var speed = 5000;
var maxLogSize = 100000; //Define the max limit of log to display  ~ 2500 lines
var currentLogSize = 0; //Define the size of log actually displayed
var last_run = "";
var runInstance = false;

$(document).ready(function () {
    $.get("/getSlapgridParameters",null,function(data) {
        runInstance = data.run_instance;
    });
});

var isRunning = function () {
    "use strict";
    if (running) {
        $("#error").Popup("Slapgrid is currently running!",
                          {type: 'alert', duration: 3000});
    }
    return running;
};

function setSpeed(value) {
    "use strict";
    if (openedlogpage === "") {
        speed = 5000;
    } else {
        speed = value;
    }
}

function clearAll(setStop) {
    "use strict";
    currentState = false;
    running = setStop;
}

function removeFirstLog() {
    "use strict";
    currentLogSize -= parseInt($("#salpgridLog p:first-child").attr('rel'), 10);
    $("#salpgridLog p:first-child").remove();
}

function writeLogs(data) {
    "use strict";
    var log_info = "",
         size = data.content.position - logReadingPosition;

    if (size < 0) {
            clearAll(false);
    }
    if (logReadingPosition !== 0 && data.content.truncated) {
            log_info = "<p  class='info' rel='0'>SLAPRUNNER INFO: SLAPGRID-LOG HAS BEEN TRUNCATED HERE. To see full log reload your log page</p>";
    }

    logReadingPosition = data.content.position;
    if (data.content.content !== "") {
            $("#salpgridLog").append(log_info + "<p rel='" + size + "'>" + data.content.content.toHtmlChar() + "</p>");
            $("#salpgridLog")
                    .scrollTop($("#salpgridLog")[0].scrollHeight - $("#salpgridLog").height());
    }
    if (running && openedlogpage !== "") {
            $("#salpgridLog").show();
            $("#manualLog").hide();
            $("#slapstate").show();
            $("#openloglist").hide();
    }
    currentLogSize += parseInt(size, 10);
    if (currentLogSize > maxLogSize) {
            //Remove the first element into log div
            removeFirstLog();
            if (currentLogSize > maxLogSize) {
                    removeFirstLog(); //in cas of previous <p/> size is 0
            }
    }
}

function getRunningState() {
    "use strict";
    var url = $SCRIPT_ROOT + "/slapgridResult",
        build_success = 0,
        run_success = 0,
        param = {
            position: logReadingPosition,
            log: (openedlogpage !== "") ? currentProcess : ""
        },
        jqxhr = $.get(url, param, function (data) {
            running = data.result;
            if (data.instance.state) {
                currentProcess = processTypes.instance;
            } else if (data.software.state) {
                currentProcess = processTypes.software;
            }
            if (last_run === "") {
                last_run = data.instance.last_build;
            }
            $("#last_build_software").text("last build: " + data.software.last_build);
            if (data.instance.last_build !== last_run) {
                currentProcess = processTypes.instance;
                last_run = data.instance.last_build;
            }
            $("#last_build_instance").text("last run: " + data.instance.last_build);
            writeLogs(data);
            setRunningState(data);
            //show accurate right panel
            if (running) {
                $("#slapstate").show();
                $("#openloglist").hide();
            }
            if(data.result) {
                if (currentProcess === processTypes.software && runInstance) {
                    updateStatus("instance", "waiting");
                }
                updateStatus(currentProcess, "running");
            } else {
               build_success = (data.software.success === 0)? "terminated":"failed";
               if ( last_run < data.software.last_build && data.software.success === 1 ) {
                   run_success = "notupdated";
               } else {
                   run_success = (data.instance.success === 0)? "terminated":"failed";
               }
               updateStatus("software", build_success);
               updateStatus("instance", run_success);
            }
        }).error(function () {
            clearAll(false);
        });
}

function stopProcess() {
    "use strict";
    if (sendStop) {
        return;
    }
    if (running) {
        sendStop = true;

        var urlfor = $SCRIPT_ROOT + "stopSlapgrid",
            type = "slapgrid-sr";

        if (currentProcess === processTypes.instance) {
            type = "slapgrid-cp";
        }
        $.post(urlfor, {type: type}, function (data) {
        })
            .error(function () {
                $("#error").Popup("Failed to stop Slapgrid process", {type: 'error', duration: 3000});
            })
            .complete(function () {
                sendStop = false;
                forcedStop = true;
            });
    }
}

function bindRun() {
    "use strict";
    $("#softrun").click(function () {
        if ($(this).hasClass('slapos_stop')) {
            stopProcess();
        } else {
            if (!isRunning()) {
                runProcess($SCRIPT_ROOT + "/runSoftwareProfile").then(function() {
                    window.location.href = $SCRIPT_ROOT + "/viewLog?logfile=software.log";
                });
            }
        }
        return false;
    });
    $("#instrun").click(function () {
        if ($("#softrun").hasClass('slapos_stop')) {
            stopProcess();
        } else {
            if (!isRunning()) {
                runProcess($SCRIPT_ROOT + "/runInstanceProfile").then(function() {
                    if (window.location.pathname === "/viewLog")
                         window.location.href = $SCRIPT_ROOT + "/viewLog?logfile=instance.log";
                });
            }
        }
        return false;
    });
}

function updateStatus(elt, val) {
  "use strict";
  var src = '#' + elt + '_run_state', value = 'state_' + val;
  $(src).removeClass();
  $(src).addClass(value);
  switch (val) {
    case "waiting":
      $(src).children('p').text("Queue");
      break;
    case "stopped":
      $(src).children('p').text("Stopped by user");
      break;
    case "terminated":
      $(src).children('p').text("Complete");
      break;
    case "running":
      $(src).children('p').text("Processing");
      break;
    case "notupdated":
      $(src).children('p').text("Not updated");
      break;
    case "failed":
      $(src).children('p').text("Failed");
      break;
  }
}

function setRunningState(data) {
    "use strict";
    if (data.result) {
        if (!currentState) {
            $("#running").show();
            running = true;
            //change run menu title and style
            if (data.software.state) {
                if ( $("#running").children('span').length === 0 ) {
                    $("#softrun").removeClass('slapos_run');
                    $("#softrun").addClass('slapos_stop');
                    if($("[class=software][id=running_info]").length === 0) {
                        $("p#running_info").remove()
                        $("#running img").before('<p id="running_info" class="software">Building software...</p>');
                    }
                }
            }
            if (data.instance.state) {
              ///Draft!!
                if ( $("#running").children('span').length === 0 ) {
                    $("#softrun").removeClass('slapos_run');
                    $("#softrun").addClass('slapos_stop');
                    if($("[class=instance][id=running_info]").length === 0) {
                        $("p#running_info").remove()
                        $("#running img").before('<p id="running_info" class="instance">Running instance...</p>');
                    }
                }
            }
        }
    } else {
        if ( $("#running").is(":visible") ) {
          $("#error").Popup("Slapgrid finished running your " + currentProcess + " profile", {type: 'info', duration: 3000});
          if ( forcedStop ) {
            updateStatus('instance', 'stopped');
            updateStatus('software', 'stopped');
          }
          else {
            updateStatus(currentProcess, 'terminated');
          }
          //Update window!!!
          $("#slapswitch").attr('rel', 'opend');
          $("#slapswitch").text('Access application');
        }
        $("#running").hide();
        $("#running_info").remove();
        $("#softrun").removeClass('slapos_stop');
        $("#softrun").addClass('slapos_run');
        if ( $("#running").children('span').length > 0 ) {
          $("#running").children('p').remove();
        }
        currentState = false;
    }
    currentState = data.result;
}

function runProcess(urlfor) {
    "use strict";
    if (!isRunning()) {
        return $.post(urlfor).then(function() {
            if ( $("#running_info").children('span').length > 0 ) {
              $("#running_info").children('p').remove();
            }
        });
    }
}
