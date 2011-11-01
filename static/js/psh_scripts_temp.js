function checkWikipedia(subjectID){
      var parent = $('#logoWikipedia').parent();
      var subject = $('#' + subjectID).text();
      var logoWikipedia = $('#logoWikipedia'); 
      parent.removeAttr('href');
      logoWikipedia.attr('class', 'inactive');
      logoWikipedia.css('opacity', '0.3');
      
      $.ajax({type: 'POST',
              url: '/psh_manager_online/wikipedia/' + subjectID,
              success: function(msg){
                  if(msg){
                    logoWikipedia.removeAttr('class');
                    logoWikipedia.css('opacity', '1');
                    parent.attr('href', 'http://cs.wikipedia.org/wiki/' + subject);
                  }
              }
              
            });
      
      $.ajax({type : 'GET',
	      dataType: 'jsonp',
              url : 'http://cs.wikipedia.org/w/api.php?action=opensearch&search=' + subject, 
              success: function(concept){
		if(concept[1].length > 0){

		  logoWikipedia.removeAttr('class');
		  logoWikipedia.css('opacity', '1');
		  parent.attr('href', 'http://cs.wikipedia.org/wiki/' + subject);
		}
              },
              data : {}
      });
}