// static/emt/js/typeahead-init.js
$(function(){
  console.log("Typeahead initialization starting...");

  var $input = $('#department-input');
  if (!$input.length) {
    console.error("#department-input not found.");
    return;
  }
  var endpoint = $input.data('url');
  console.log("Found #department-input, data-url=", endpoint);

  var deptEngine = new Bloodhound({
    datumTokenizer: Bloodhound.tokenizers.obj.whitespace('text'),
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
      // must specify `url` and `wildcard`!
      url: endpoint + '?q=%QUERY',
      wildcard: '%QUERY',
      transform: function(response) {
        console.log("Got response:", response);
        // map your API’s [{id,text},…] to Bloodhound’s format
        return response.map(function(item){
          return {
            id:   item.id,
            text: item.text
          };
        });
      }
    }
  });

  $input.typeahead(
    {
      hint:      true,
      highlight: true,
      minLength: 1
    },
    {
      name:    'departments',
      display: 'text',
      source:  deptEngine,
      limit:   10,
      templates: {
        suggestion: function(item) {
          return '<div>' + item.text + '</div>';
        }
      }
    }
  ).on('typeahead:select', function(ev, sel){
    console.log("Selected:", sel);
  });
});
