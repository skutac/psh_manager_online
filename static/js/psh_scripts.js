var currentSuggested = $('#suggestedSubjects li.hidden');
var screenheight = screen.height;
$(document).ready(function(){
    $('#scrollDiv, #scrollable').css('height', (screenheight-200));
    $('#mainTree').load('static/html/tree.html', function(){
        var split = window.location.hash.split("#!");
        if(split.length == 1){
           getConcept("PSH1");
	   checkWikipedia('PSH1');
        }
        else{
           var subjectID = split[1];
           var current = $("#" + subjectID);
	   var subject = current.text();
	   getConcept(subjectID);
	   saveToCache(subject, subjectID);
	   unwrap(current);
	   highlight(current);
        }
    });


    $('#mainTree').delegate('.heslo', 'click', function() {
      var subjectID = $(this).attr('id');
      var current = $(this);
      var subject = current.text();
      getConcept(subjectID);
      saveToCache(subject, subjectID);
      var test = $(current).next();
      if(test.get(0) != undefined){ 
        if(test.get(0).nodeName == 'UL'){
        if(test.is(":visible")){
            test.slideUp('slow');
            $(this).css('background-image', 'url(static/img/1.png)');
        }
        else{
            test.slideDown('slow');
            $(this).css('background-image', 'url(static/img/1_down.png)');
        }
      }}
      highlight(current);
});
    
$("#search").delegate('#pshSuggest', 'keyup', function(event){
    var textInput = $(this).val();
    if(textInput.length > 1){
        var english = $('#english').attr('class');
        var keycode = (event.keyCode ? event.keyCode : event.which);
        if(keycode == '13'){
            var subject = $(this).val();
            getSuggestedSubject(subject);
        }
        $.ajax({type : "POST",
               url : "suggest",
               datatype: "json",
               success: function(data){
                      $("#pshSuggest").autocomplete({source: data});},
               data : {'input': textInput, 'en': english}
        });
    }
    else{
        $("#suggestedSubjects").html("");
    }
});

$("body").delegate(".heslo", "click", function(){
    var subjectID = $(this).attr("itemid");
    if(!(subjectID)){
      subjectID = $(this).attr("id");
    }
    window.location.hash = "!" + subjectID;
    return false;
});

$(window).bind("hashchange", function(){
  var split = window.location.hash.split("#!")
  if (split.length == 1){
    return
  }
  else{
    subjectID = split[1];
    var current = $("#" + subjectID);
    var subject = current.text();
    getConcept(subjectID);
    saveToCache(subject, subjectID);
    unwrap(current);
    highlight(current);
  }
   
});

});

function getSuggestedSubject(subject){
    var english = $('#english').attr('class');
    $.ajax({type : "POST",
               url : "getID",
               success: function(subjectID){
                        if(subjectID == "None"){
                            $('#pshSuggest').val("");
                            $('ul.ui-autocomplete').hide();
                            getSearchResult(subject, english);
			    window.location.hash = "";
                        }
                        else{
                            var current = $('#' + subjectID);
			    window.location.hash = "!" + subjectID;
//                             getConcept(subjectID);
//                             saveToCache(subject, subjectID);
//                             unwrap(current);
//                             highlight(current);
                            $('#pshSuggest').val("");
                        }
                       }, 
               data : {'input': subject, 'en': english}
    });
}

function getSearchResult(subject, english){
    $.ajax({type : 'POST',
              url : 'getSearchResult', 
              success: function(subjects){
//                        $('#concept').html(concept).hide();
                          $('#concept').html(subjects);
//                        $('#concept').fadeIn('slow');
                       },
              data : {substring : subject, english : english}
      });
}

$('.ui-menu-item a').live('click', function(){
    var subject = $(this).text();
    getSuggestedSubject(subject);
});

$('#english').live('click', function(){
    var mode = $(this).attr('class');
    if(mode == "inactive"){
        $(this).css('opacity', '0.9');
        $(this).attr('class', 'active');
        $('#searchLanguage').text('angličitna');
    }
    else{
        $(this).css('opacity', '0.2');
        $(this).attr('class', 'inactive');
        $('#searchLanguage').text('čeština');
    }
});

$('.clickable').live('click', function() {
      var subjectID = $(this).attr('itemid');
      var subject = $(this).text();
      var current = $('#' + subjectID);
      getConcept(subjectID);
      saveToCache(subject, subjectID);
      unwrap(current);
      highlight(current);
});

$('#cacheList li').live('click', function() {
    var subjectID = $(this).attr('itemid');
    var current = $('#' + subjectID);
    getConcept(subjectID);
    unwrap(current);
    highlight(current);
});

function setMARCLink(){
    var sysno = $("#pshID").attr("data-sysno");
    $("#marc_link").attr("href", "http://aleph.techlib.cz/F?func=direct&local_base=STK10&doc_number=" + sysno + "&format=001");
    return
}

function saveToCache(subject, subjectID){
    var test = $('.cache').filter(function() {
        return $(this).attr('itemid') == subjectID;
    });
    if(test.text() == ""){
        var cache = $('#cacheList li.active');
        cache.text(subject);
        cache.attr('itemid', subjectID);
        cache.attr('class', 'inactive cache heslo');
        var nextCache = $(cache).next();
        if(nextCache.get(0) != undefined){
            nextCache.attr('class', 'active cache heslo');
        }
        else{
            $('#cacheList li:first').attr('class', 'active cache heslo');
        }
    }
}

function highlight(li){
    $('li').css('color', 'black');
    li.css('color', 'red');
    var subject = li.text();
    var subjectID = li.attr('id');
//     alert(li.offset().top);
//     alert($('#scrollable').scrollTop());
    $('#katalog').parent().attr('href','http://aleph.techlib.cz/F/?func=find-b&request=' + encodeURIComponent(subject) + '&find_code=PSH&adjacent=N&local_base=STK&x=26&y=5&filter_code_1=WLN&filter_request_1=&filter_code_2=WYR&filter_request_2=&filter_code_3=WYR&filter_request_3=&filter_code_4=WFM&filter_request_4=&filter_code_5=WSL&filter_request_5=&pds_handle=GUEST');
    $('#scrollable').animate({scrollTop:($('#scrollable').scrollTop() + li.offset().top - screenheight/2)}, 1000);
}

function getConcept(subjectID){
    $.ajax({type : 'POST',
              url : './getConcept', 
              success: function(concept){
                       $('#concept').html(concept).hide();
                       checkWikipedia(subjectID);
                       setMARCLink();
                       $('#concept').fadeIn('slow');
                       },
              data : {subjectID : subjectID}
      });
}

function unwrap(current){
      var test = $(current).next();
      $(current).parents().show('slow');
      $(current).parents('ul').each(function(){
//       $(this).show('slow');
      $(this).prev('li').css('background-image', 'url(static/img/1_down.png)');
      });
      if(test.get(0) != undefined){ 
        if(test.get(0).nodeName == 'UL'){
        if(test.is(":hidden")){
            test.slideDown('slow');
            $(current).css('background-image', 'url(static/img/1_down.png)');
        }
      }}
     return false; 
}

function checkWikipedia(subjectID){
      var parent = $('#logo_wikipedia').parent();
      var subject = $('#' + subjectID).text();
      var logoWikipedia = $('#logo_wikipedia'); 
      parent.removeAttr('href');
      logoWikipedia.attr('class', 'inactive');
      logoWikipedia.css('opacity', '0.3');
      
      $.ajax({type: 'POST',
              url: 'wikipedia',
              data : {subjectID: subjectID},
              success: function(msg){
//                   console.log("---- Get wikipedia link:" + msg + " ----");
                  if(msg != ""){
                    logoWikipedia.removeAttr('class');
                    logoWikipedia.css('opacity', '1');
                    parent.attr('href', msg);
                  }
                  //else{
                    //$.ajax({type : 'GET',
	                    //dataType: 'jsonp',
                            //url : 'http://cs.wikipedia.org/w/api.php?action=opensearch&search=' + subject, 
                            //success: function(concept){
		              //if(concept[1].length > 0){
		                  //logoWikipedia.removeAttr('class');
		                  //logoWikipedia.css('opacity', '1');
		                  //parent.attr('href', 'http://cs.wikipedia.org/wiki/' + subject);
                                  //saveWikipediaLink(subjectID);
		              //}
                            //},
                            //data : {}
                    //});
                  //}
              }
            });
}

function saveWikipediaLink(subjectID){
//     console.log("---- Saving wikipedia link: " + subjectID + " ----");
    $.ajax({type: 'POST',
            url: 'saveWikipediaLink',
            success: function(msg){
//                 console.log(msg);
            },
            data: {subjectID:subjectID},
    });
}

