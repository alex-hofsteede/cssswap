$(function() {
  window.editors = [];

  $( "#edit-tabs" ).tabs({
    show: function(event,ui) {
      if($(ui.panel).find('.CodeMirror').length == 0) {
        $(ui.panel).find('textarea').each(function(index,item){
            var editor = CodeMirror.fromTextArea(item)
            window.editors.push(editor);
        });
      }
    }
  });

  $('#edit-css-form').submit(function() {
    _.each(window.editors, function(editor) {
      console.log('saving');
      editor.save();
    });
  });
});
