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
    _.each(window.editors,saveEditor);
  });
});

function saveEditor(editor){
  console.log('saving');
  editor.save();
}

function newPreview(rawHtmlUrl){
    _.each(window.editors,saveEditor);
    if(!window.rawHtml || window.rawHtml == "")
        $.get(rawHtmlUrl,{},function(rawHtml){window.rawHtml = rawHtml; buildPreview(rawHtml);})
    else
        buildPreview(window.rawHtml);
}

window.delimiter = "--REPLACE--";
function buildPreview(rawHtml){
    var pattern = RegExp(window.delimiter+"([0-f]+)"+window.delimiter,"g"); 
    var stylesheets = {};
    //$($.makeArray($('#edit-css-form')[0].elements)).each(function(index,element){
    _.each($('#edit-css-form')[0].elements,function(index,element){
        stylesheets[element.name] = element.value;
        });
//editform.elements.forEach(function(index,element){stylesheets[element.name] = element.value;});
//    for (var element in editform.elements)
//        stylesheets[element.name] = element.value;
    previewHtml = rawHtml.replace(pattern,function(match,p1){
        return stylesheets['cssasset_'+p1];
        }); 
    displayPreview(previewHtml);
}

function displayPreview(previewHtml){
    if(!window.previewdoc){
        var iframe = document.createElement("iframe");
        document.body.appendChild(iframe);
        window.previewdoc = iframe.document;
        if(iframe.contentDocument)
            window.previewdoc = iframe.contentDocument;
        else if(iframe.contentWindow.document)
            window.previewdoc = iframe.contentWindow.document;
    }
    window.previewdoc.open();
    window.previewdoc.writeln(previewHtml);
    window.previewdoc.close();
}
