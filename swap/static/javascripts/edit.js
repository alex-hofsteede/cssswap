$(function() {
  window.editors = [];

  $( "#edit-tabs" ).tabs({
    show: function(event,ui) {
      if($(ui.panel).find('.CodeMirror').length == 0) {
        var editor = CodeMirror.fromTextArea($(ui.panel).find('textarea')[0])
        window.editors.push(editor);
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
