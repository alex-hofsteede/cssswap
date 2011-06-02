$(function() {
  console.log('load');
  $( "#edit-tabs" ).tabs();
  $('#edit-tabs textarea').each(
    function() {
    console.log(this);
    console.log('test');
    CodeMirror.fromTextArea(this);
  }
  );
  /*
   *var myCodeMirror = CodeMirror.fromTextArea($('#edit-tabs textarea')[0]);
   */
});
