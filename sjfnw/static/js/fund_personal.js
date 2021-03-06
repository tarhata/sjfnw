//constants
var status_texts = { //for ajax error messages
  400: '400 Bad request',
  401: '401 Unauthorized',
  403: '403 Forbidden',
  404: '404 Not found',
  408: '408 Request timeout',
  500: '500 Internal server error',
  503: '503 Service unavailable',
  504: '504 Gateway timeout'
};

//general display
function datepicker() { //date input fields
  $.datepicker.setDefaults({
    dateFormat: 'mm/dd/yy',
    minDate: 0,
    hideIfNoPrevNext: true,
    constrainInput: false
  });
  $( ".datePicker" ).datepicker();
}

//ajax - general
var request_processing = false;
function startProcessing() {
  request_processing = true;
  //console.log('Request processing');
  var loader = document.getElementById('ajax_loading');
  if (loader) {
    loader.style.display = "";
  }
}

function endProcessing() {
  request_processing = false;
  //console.log('Request complete');
  var loader = document.getElementById('ajax_loading');
  if (loader) {
    loader.style.display = "none";
  }
}

/** Submits form data, displays errors or redirects if successful
 * 
 * @param sub_url Url to send form data to
 * @param form_id
 * @param div_id
 * @param date
 * @param dasked
 * @param dpromised
 *
 */
function Submit(sub_url, form_id, div_id, date, dasked, dpromised){
  if (request_processing) {
    console.log('Request processing; submit denied');
    return false;
  }
  startProcessing();
  console.log('Submission to ' + sub_url + ' requested');
  $.ajax({
    url:sub_url,
    type:"POST",
    data:$(form_id).serialize(),
    timeout: 10000,
    success:function(data, textStatus, jqXHR){
      trackEvents(sub_url, div_id, 'POST');
      if (jqXHR.responseText=="success") { //successful
        console.log('Submission to ' + sub_url + ' returned success; redirecting');
        if (sub_url.match('add-contacts')) {
          setTimeout(function() {location.href= '/fund/?load=stepmult#your-contacts';}, 200);
        } else {
          setTimeout(function() {location.href='/fund/';}, 200);
        }
      } else { //errors
        console.log('Submission to ' + sub_url + ' returned text');
        document.getElementById(div_id).innerHTML=jqXHR.responseText;
        if (sub_url.match('done')) {
          var pks = sub_url.match(/\d+/g);
          if (pks && pks[1]) {
            completeLoaded(pks[1], dasked, dpromised, 'True');
          }
        }
      }
      if (date) { datepicker();}
      endProcessing();
    },
    error:function(jqXHR, textStatus, errorThrown){
      endProcessing();
      var errortext = ''
        if (status_texts[jqXHR.status]) {
          errortext = status_texts[jqXHR.status]
        } else if (textStatus=='timeout') {
          errortext = 'Request timeout'
        } else {
          errortext = (jqXHR.status || '') + ' Unknown error';
        }
      document.getElementById(div_id).innerHTML='<p>An error occurred while handling your request.  We apologize for the inconvenience.</p><p>URL: POST ' + sub_url + '<br>Error: ' + errortext + '</p><p><a href="/fund/support" target="_blank">Contact us</a> for assistance if necessary.  Please include the above error text.</p>'
        console.log('Error submitting to ' + sub_url + ': ' + errortext);
      if (date) {
        datepicker();
      }
    }
  });
}

//analytics events
function trackEvents(url, div_id, request_type) { //analytics events
  //console.log('trackEvents', url, div_id, request_type);
  var category;
  var action;
  if (div_id.search('addmult') > -1) {
    // console.log('addmult');
    if (request_type == 'POST') {
      action = 'Add multiple - submit';
    } else {
      action = 'Add multiple - load';
    }
    if (url.search('addmult') > -1) {
      category = 'Contacts';
    } else if (url.search('stepmult') > -1) {
      category = 'Steps';
    }
  } else if (div_id.search('nextstep') > -1) {
    //console.log('nextstep');
    category = 'Steps';
    if (url.search(/\d+$/) > -1 && request_type == 'POST') {
      action = 'Edit';
    } else if (url.search(/done$/) > -1) {
      if (request_type == 'POST') {
        action = 'Complete step - submit';
      } else {
        action = 'Complete step - load';
      }
    }
  } else if (request_type == 'POST') {
    //console.log('POST');
    if (url.search(/step$/) > -1) {
      category = 'Steps';
      action = 'Add';
    } else if (url.search(/delete$/) > -1) {
      category = 'Contacts';
      action = 'Delete';
    } else if (url.search(/edit$/) > -1) {
      category = 'Contacts';
      action = 'Edit';
    }
  }
  console.log('trackEvents', category, action)
    if (category && action) {
      _gaq.push(['_trackEvent', category, action]);
    }
}

//suggested steps
var sug_div;
function showSuggestions(inp) { //shows suggested steps
  if (sug_div) { sug_div.style.display="none"; } //hides prior set
  var patt = new RegExp('\\d+');
  var num = patt.exec(inp);
  sug_div = document.getElementById('suggest_'+num);
  sug_div.style.display="block";
}

function suggestFill(source, target) { //fills input with selected step
  var text = source.innerHTML;
  if (target) {
    document.getElementById(target).value=text;
  } else {
    document.getElementById('id_description').value=text;
  }
}
