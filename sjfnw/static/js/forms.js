/** Shared form functions - utils, autosave, file handling **/

/**----------------------------- formUtils ---------------------------------**/
var formUtils = {};

formUtils.loading_image = '<img src="/static/images/ajaxloader2.gif" height="16" width="16" alt="Loading...">';

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


formUtils.init = function(url_prefix, draft_id, submit_id, user_id, staff_user) {
  if (staff_user){
    formUtils.staff_user = staff_user;
  } else {
    formUtils.staff_user = '';
  }
  autoSave.init(url_prefix, submit_id, user_id);
  fileUploads.init(url_prefix, draft_id);
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

/**------------------------------- autoSave --------------------------------**/

var autoSave = {};
autoSave.save_timer = false;
autoSave.pause_timer = false;

/* autosave flow:

   page load -> init ->
               focus -> resume() -> sets onblur, sets save_timer -30-> save()
   page blur -> pause() -> sets onfocus, sets pause_timer -30-> clears save_timer

*/

autoSave.init = function(url_prefix, submit_id) {
  autoSave.submit_url = '/' + url_prefix + '/' + submit_id;
  autoSave.save_url = autoSave.submit_url + '/autosave';
  if (user_id) {
    autoSave.user_id = user_id;
  } else {
    autoSave.user_id = '';
  }
  console.log('Autosave variables loaded');
  autoSave.resume();
};


autoSave.pause = function() {
  if ( !window.onfocus ) {
    console.log(formUtils.logTime() + 'autoSave.pause called; setting timer');
    // pause auto save
    autoSave.pause_timer = window.setTimeout(function(){
       console.log(formUtils.logTime() + 'autoSave.pause_timer up, pausing autosave');
       window.clearInterval(autoSave.save_timer);
       autoSave.pause_timer = false;
       }, 30000);
    // set to resume when window gains focus
    $(window).on('focus', autoSave.resume);
    // don't watch for further blurs
    $(window).off('blur');
  } else {
    console.log(formUtils.logTime() + 'autoSave.pause called, but already paused');
  }
};

autoSave.resume = function() {
  if ( !window.onblur ) { // avoid double-firing
    console.log(formUtils.logTime() + ' autoSave.resume called');
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
    console.log(formUtils.logTime() + ' window already has onblur');
  }
};

autoSave.save = function (submit, override){
  if (!override){ override = 'false'; }
  console.log(formUtils.logTime() + "autosaving");
  console.log($('form').serialize());
  $.ajax({
    url: autoSave.save_url,
    type:"POST",
    data:$('form').serialize() + '&user_id=' + autoSave.user_id,
    success:function(data, textStatus, jqXHR){
      if (jqXHR.status==200) {
        if (submit) { //trigger the submit button
          var submit_all = document.getElementById('hidden_submit_app');
          submit_all.click();
        } else { //update 'last saved'
          $('.autosaved').html(formUtils.currentTimeDisplay());
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
        } else if (formUtils.status_texts[jqXHR.status]) {
          errortext = formUtils.status_texts[jqXHR.status];
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

/**------------------------------------ FILE UPLOADS -------------------------------------------**/
var fileUploads = {};

fileUploads.uploading = false;
fileUploads.uploading_span = '';
fileUploads.current_field = '';

fileUploads.init = function(url_prefix, draft_id) {
  fileUploads.get_url = '/get-upload-url/?type=' + url_prefix + '&id=' + draft_id;
  fileUploads.remove_url = '/' + url_prefix + '/' + draft_id + '/remove/';
  $('[type="file"]').change(function() {
      fileUploads.fileChanged(this.id);
    });
  console.log('fileUploads vars loaded, file fields scripted');
};

/* each file field has its own form. html element ids use this pattern:
  input field: 							'id_' + fieldname
  form: 										fieldname + '_form'
  span for upload status: 	fieldname + '_uploaded'
  submit button: 						fieldname + '_submit' */

fileUploads.clickFileInput = function(event, input_id) {
  /* triggered when "choose file" label is clicked
     transfers the click to the hidden file input */
  console.log(event);
  console.log('clickFileInput' + input_id);
  var input = document.getElementById(input_id);
  if (input) {
    input.control.click();
    console.log('Clicked it');
  } else {
    console.log('Error - no input found');
  }
};

fileUploads.fileChanged = function(field_id) {
  /* triggered when a file is selected
     show loader, call getuploadurl */
  console.log('fileChanged');
  if (fileUploads.uploading) {
    console.log('Upload in progress; returning');
    return false;
  }
  console.log(field_id + " onchange");
  var file = document.getElementById(field_id).value;
  console.log("Value: " + file);
  if (file) {
    fileUploads.uploading = true;
    fileUploads.current_field = field_id.replace('id_', '');
    fileUploads.uploading_span = document.getElementById(field_id.replace('id_', '') + '_uploaded');
    fileUploads.uploading_span.innerHTML = formUtils.loading_image;
    fileUploads.getUploadURL();
  }
};

fileUploads.getUploadURL = function() {
  console.log('getUploadURL');
  $.ajax({
    url: fileUploads.get_url,
    success: function(data) {
      console.log('current field: ' + fileUploads.current_field);
      var cform = document.getElementById(fileUploads.current_field + '_form');
      cform.action = data;
      var cbutton = document.getElementById(fileUploads.current_field + '_submit');
      cbutton.click();
    }
  });
};

fileUploads.iframeUpdated = function(iframe) { //process response
  console.log(formUtils.logTime() + 'iframeUpdated');
  var results = iframe.contentDocument.body.innerHTML;
  console.log("The iframe changed! New contents: " + results);
  if (results) {
    var field_name = results.split("~~")[0];
    var linky = results.split("~~")[1];
    var file_input = document.getElementById('id_' + field_name);
    if (file_input && linky) {
      fileUploads.uploading_span.innerHTML = linky;
    } else {
      fileUploads.uploading_span.innerHTML = 'There was an error uploading your file. Try again or <a href="/apply/support">contact us</a>.';
    }
    fileUploads.uploading = false;
  }
};

fileUploads.removeFile = function(field_name) {
  $.ajax({
    url: fileUploads.remove_url + field_name + formUtils.staff_user,
    success: function(data) {
      r_span = document.getElementById(field_name + '_uploaded');
      r_span.innerHTML = '<i>no file uploaded</i>';
    }
  });
};


