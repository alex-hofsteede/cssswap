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

  $('#edit-css-form').submit(function(event) {
    event.preventDefault();
    _.each(window.editors, function(editor) {
      console.log('saving');
      editor.save();
    });
    $.post($(this).attr('action'),$(this).serialize(),formSubmitResult)
  });
});


function formSubmitResult(resultStr)
{
    var iframe = document.createElement("iframe");
    document.body.appendChild(iframe);
    if(!window.previewdoc){
        window.previewdoc = iframe.document;
        if(iframe.contentDocument)
            window.previewdoc = iframe.contentDocument;
        else if(iframe.contentWindow.document)
            window.previewdoc = iframe.contentWindow.document;
    }
    window.previewdoc.open();
    window.previewdoc.writeln(resultStr);
    window.previewdoc.close();
}
