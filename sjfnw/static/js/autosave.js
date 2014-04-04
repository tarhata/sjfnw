/** Shared form functions - utils, autosave, file handling **/

/**----------------------------- formUtils ---------------------------------**/
var formUtils = {}; 

formUtils.status_texts = { //for ajax error messages
  400: '400 Bad request',
  401: '401 Unauthorized',
  403: '403 Forbidden',
  404: '404 Not found',
  408: '408 Request timeout',
  500: '500 Internal server error',
  503: '503 Service unavailable',
  504: '504 Gateway timeout'
};

formUtils.currentTimeDisplay = function(){
  /* returns current time as a string. format = May 12, 2:45p.m. */
  var monthNames = [
      "January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December"];
  var d = new Date();
  var h = d.getHours();
  var m = d.getMinutes();
  /*var s = d.getSeconds();*/
  var dd = "a.m.";
  if (h >= 12) {
    h = h-12;
    dd = "p.m.";
  }
  if (h === 0) {
    h = 12;
  }
  m = m<10?"0"+m:m;
  /* s = s<10?"0"+s:s; */
  return monthNames[d.getMonth()]+' '+d.getDate()+', '+h+':'+m+dd;
};

formUtils.logTime = function (){
  /* returns current time as a string for console logs. hh:mm:ss */
  var d = new Date();
  var m = d.getMinutes();
  m = m<10?"0"+m:m;
  return d.getHours() + ':' + m + ':' + d.getSeconds() + ' ';
};

/**------------------------------- autoSave --------------------------------**/

var autoSave = {};
autoSave.save_timer = false;
autoSave.pause_timer = false;

  /* autosave flow:

     page load -> init ->
                 focus -> resume() -> sets onblur, sets save_timer -30-> save()
     page blur -> pause() -> sets onfocus, sets pause_timer -30-> clears save_timer

  */

autoSave.init = function(url_prefix, save_id, submit_id, staff_user) {
  autoSave.get_upload_url = '/get-upload-url/?t=' + url_prefix;
  autoSave.autosave_url = url_prefix + '/' + save_id + '/autosave';
  autoSave.submit_url = url_prefix + '/' + submit_id;
  if (staff_user){
    autoSave.staff_user = staff_user;
  } else {
    autoSave.staff_user = false;
  }
  console.log('Autosave variables loaded');
};

 
autoSave.pause = function() {
  if ( !window.onfocus ) {
    console.log(logTime() + 'autoSave.pause called; setting timer');
    // pause auto save
    autoSave.pause_timer = window.setTimeout(function(){
       console.log(logTime() + 'autoSave.pause_timer up, pausing autosave');
       window.clearInterval(autoSave.save_timer);
       autoSave.pause_timer = false;
       }, 30000);
    // set to resume when window gains focus
    $(window).on('focus', autoSave.resume);
    // don't watch for further blurs
    $(window).off('blur');
  } else {
    console.log(logTime() + 'autoSave.pause called, but already paused');
  }
};

autoSave.resume = function() {
  if ( !window.onblur ) { // avoid double-firing
    console.log(logTime() + ' autoSave.resume called');
    // reload the pause binding
    $(window).on('blur', autoSave.pause);
    if (autoSave.pause_timer) {
      // clear timer if window recently lost focus (autosave is still going)
      console.log('pause had been set; clearing it');
      window.clearTimeout(autoSave.pause_timer);
      autoSave.pause_timer = false;
    } else {
      // set up save timer
      console.log('Setting autosave interval');
      autoSave.save_timer = window.setInterval("autoSave.save()", 30000);
    }
    // unload the resume binding
    $(window).off('focus');
  } else {
    console.log(logTime() + ' window already has onblur');
  }
};

autoSave.save = function (submit, override){
  if (!override){ override = 'false'; }
  console.log(logTime() + "autosaving");
  $.ajax({
    url:"/apply/{{ cycle.pk }}/autosave/{{ user_override|default:'?'}}&override=" + override,
    type:"POST",
    data:$('form').serialize() + '&user_id=' + user_id,
    success:function(data, textStatus, jqXHR){
      if (jqXHR.status==200) {
        if (submit) { //trigger the submit button
          var submit_all = document.getElementById('hidden_submit_app');
          submit_all.click();
        } else { //update 'last saved'
          $('.autosaved').html(currentTimeDisplay());
        }
      } else { //unexpected status code
        $('.autosaved').html('Unknown error<br>If you are seeing errors repeatedly please <a href="/apply/support#contact">contact us</a>');
      }
    },
    error:function(jqXHR, textStatus, errorThrown){
      var errortext = '';
      if (jqXHR.status==409){ //conflict - pause autosave and confirm override
        window.clearInterval(autoSave.save_timer);
        showOverrideWarning(2);
      } else {
        if(jqXHR.status==401){
          location.href = jqXHR.responseText + '?next=' + location.href;
        } else if (status_texts[jqXHR.status]) {
          errortext = status_texts[jqXHR.status];
        } else if (textStatus=='timeout') {
          errortext = 'Request timeout';
        } else {
          errortext = 'Unknown error';
        }
        $('.autosaved').html('Error: ' + errortext + '<br>If you are seeing errors repeatedly please <a href="/apply/support#contact">contact us</a>');
      }
    }
  });
};

  /** CHARACTER LIMITS **/
  function charLimitDisplay(area, limit){
    var counter = document.getElementById(area.name + '_counter');
    var words = area.value.match(/[^ \r\n]+/g) || [];
    //console.log(words);
    var diff = limit - words.length;
    if (diff >= 0) {
      counter.innerHTML = diff + ' words remaining';
      counter.className = 'char_counter_ok';
    } else {
      counter.innerHTML = -diff + ' words over the limit';
      counter.className = 'char_counter_over';
    }
  }

  /** FILE UPLOADS **/
  var uploading = false;
  var uploading_span;
  var current_field;

  /* each file field has its own form. html element ids use this pattern:
    input field: 							'id_' + fieldname
    form: 										fieldname + '_form'
    span for upload status: 	fieldname + '_uploaded'
    submit button: 						fieldname + '_submit' */

  function clickFileInput(event, input_id) {
    console.log(event);
    console.log('clickFileInput' + input_id);
    var input = document.getElementById(input_id);
    if (input) {
      input.control.click();
      console.log('Clicked it');
    } else {
      console.log('Error - no input found');
    }
  }

  function fileChanged(field_id) { //file selected - show loader, call getuploadurl
    console.log('fileChanged');
    if (uploading) {
      console.log('Upload in progress; returning');
      return false;
    }
    console.log(field_id + " onchange");
    var file = document.getElementById(field_id).value;
    console.log("Value: " + file);
    if (file) {
      uploading = true;
      current_field = field_id.replace('id_', '')
      uploading_span = document.getElementById(field_id.replace('id_', '') + '_uploaded');
      uploading_span.innerHTML = '<img src="/static/images/ajaxloader2.gif" height="16" width="16" alt="Loading...">';
      getUploadURL();
    }
  }

  function getUploadURL() {
    console.log('getUploadURL');
    $.ajax({
      url: '/get-upload-url/{{ draft.pk }}',
      success: function(data) {
        var cform = document.getElementById(current_field + '_form');
        cform.action = data;
        var cbutton = document.getElementById(current_field + '_submit');
        cbutton.click();
      }
    });
  }

  function iframeUpdated(iframe) { //process response
    console.log(logTime() + 'iframeUpdated');
    var results = iframe.contentDocument.body.innerHTML;
    console.log("The iframe changed! New contents: " + results);
    if (results) {
      var field_name = results.split("~~")[0];
      var linky = results.split("~~")[1];
      var file_input = document.getElementById('id_' + field_name);
      if (file_input && linky) {
        uploading_span.innerHTML = linky;
      } else {
        uploading_span.innerHTML = 'There was an error uploading your file. Try again or <a href="/apply/support">contact us</a>.';
      }
      uploading = false;
    }
  }

  function removeFile(field_name) {
    $.ajax({
      url: '/apply/{{ draft.pk }}/remove/' + field_name + '{{ user_override|default:''}}',
      success: function(data) {
        r_span = document.getElementById(field_name + '_uploaded');
        r_span.innerHTML = '<i>no file uploaded</i>';
      }
    });
  }

  /** user id and override **/
  var user_id = '';

  function setUserID() {
    var chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    var result = '';
    for (var i = 16; i > 0; --i){
      result += chars[Math.round(Math.random() * (chars.length - 1))];
    }
    user_id = result;
    console.log(user_id);
  }

  function showOverrideWarning(ver){
    window.scrollTo(0, 0);
    console.log('scrolled, showing override');
    $('#override_dialog'+ver).dialog({
      title: 'Warning: simultaneous editing',
      modal: true,
      buttons: [{
        text:'Proceed anyway',
        click: function(){
            console.log('override!');
            $('#override_dialog'+ver).dialog("close");
            autoSave(false, override=true);
            autoSave.resume();
          }
        },{
            text:'Cancel',
            click: function(){ location.href = '/apply/'; }
        }
      ],
      closeOnEscape: false,
      resizable: false,
      position: {my: 'top', at: 'top', of: '#org_wrapper'},
      width:400
    });
  }

};

