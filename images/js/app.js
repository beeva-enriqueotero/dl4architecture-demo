(function() {
  var morphSearch = document.getElementById( 'morphsearch' ),
  input = morphSearch.querySelector( 'input.morphsearch-input' ),
  ctrlClose = morphSearch.querySelector( 'span.morphsearch-close' ),
  isOpen = isAnimating = false,
  // show/hide search area
  toggleSearch = function(evt) {
    // return if open and the input gets focused
    if( evt.type.toLowerCase() === 'focus' && isOpen ) return false;

    var offsets = morphsearch.getBoundingClientRect();
    if( isOpen ) {
      classie.remove( morphSearch, 'open' );

      // trick to hide input text once the search overlay closes
      // todo: hardcoded times, should be done after transition ends
      if( input.value !== '' ) {
        setTimeout(function() {
          classie.add( morphSearch, 'hideInput' );
          setTimeout(function() {
            classie.remove( morphSearch, 'hideInput' );
            input.value = '';
          }, 300 );
        }, 500);
      }

      input.blur();
    }
    else {
      classie.add( morphSearch, 'open' );
    }
    isOpen = !isOpen;
  };

  // events
  input.addEventListener( 'focus', toggleSearch );
  ctrlClose.addEventListener( 'click', toggleSearch );
  // esc key closes search overlay
  // keyboard navigation events
  document.addEventListener( 'keydown', function( ev ) {
    var keyCode = ev.keyCode || ev.which;
    if( keyCode === 27 && isOpen ) {
      toggleSearch(ev);
    }
  } );


  /***** for demo purposes only: don't allow to submit the form *****/
  morphSearch.querySelector( 'button[type="submit"]' ).addEventListener( 'click', function(ev) { ev.preventDefault(); } );
})();



// Deep Learning demo controller class
var AppController = new function(){

  // Local vars
  var _resultZone = $("#result");
  var _searchZone = $(".morphsearch-content");
  var _searchResult = _searchZone.find("#searchZone");
  var _submitButton = $(".morphsearch-submit");
  var _closeSearchButton = $(".morphsearch-close");
  var _findRoute = $("#findRoute");
  var _modal = $(".modal").modal("hide");
  var _currentProgress = 0;
  var _maxProgress = 3;
  var _city = "";


  // Functions
  var _reset = function(){
    _resultZone.find(".thumb").remove();
    _searchResult.find(".thumb").remove();
    _resultZone.hide();
    _searchZone.hide();
    _findRoute.hide();
  }

  var findImages = function(search){

    _reset();
    var servicePath = "/getallimages?city="+search;
    _city = search;
    $.getJSON( servicePath,
      function( data ) {
        var imgs = data.result;
        var template = $('#foundImgsTmpl').html();
        Mustache.parse(template);
        var rendered = "";
        for (var i = 0; i < imgs.length; i++) {
          rendered = Mustache.render(template, imgs[i]);
          _searchResult.append(rendered);
        }
        _setImgBehaviour();
        _searchZone.show();
      }
    );

  }

  var _setProgress = function(value){

    var _progressBar = _modal.find(".progress-bar");
    var _progressText = _modal.find(".modal-title");

    _progressBar.text(value+"%");
    _progressBar.width(value+"%");
    _progressBar.attr("aria-valuenow",value);

  }

  var getResult = function(fromImg, toImg){

    var servicePath = "/findpath?from="+fromImg+"&to="+toImg+"&city="+_city;

    $.getJSON( servicePath,
      function( data ) {
        var imgs = data.result;
        var template = $('#resultTmpl').html();
        Mustache.parse(template);
        var rendered = "";
        for (var i = 0; i < imgs.length; i++) {
          rendered = Mustache.render(template, imgs[i]);
          _resultZone.append(rendered);
        }
        _closeSearchButton.click();
        _resultZone.show();
      }
    );

  }

  var getProgress = function(){

    _modal.show();
    _modal.modal("show");

    $.ajax({

      type: "GET",
      url: "/getprogress",
      data: {}

    })
    .done(function(data) {
      //console.log( "Progress call success with " + data );
      if (data < _maxProgress){
        window.setTimeout("AppController.getProgress()", 500);
        _currentProgress = data;
        _modal.modal("show");
        _setProgress(_currentProgress*33);
      } else {
        _currentProgress = data;
        _setProgress(_currentProgress);
        _modal.modal("hide");
        _modal.hide();
        _currentProgress = 0;
      }
    });
    /*.fail(function() {
    alert( "error" );
  })
  .always(function() {
  alert( "complete" );
});*/


}



var _fromImg = "";
var _toImg = "";
var _setImgBehaviour = function(){
  _fromImg = "";
  _toImg = "";
  $(".morphsearch-content .thumb a").click(
    function(){
      var url = $(this).find("img").attr("src");
      var idImg = $(this).find("img").attr("meta-id");
      if (_fromImg == ""){
        //_fromImg = url;
        _fromImg = idImg;
        $(this).addClass("fromImg");
      } else if (_toImg == ""){
        //_toImg = url;
        _toImg = idImg;
        $(this).addClass("toImg");
        _findRoute.show();
      }
    }
  )
}

// Basic constructor
var _constructor = function(){
  _reset();
  _submitButton.click(
    function(){

      var searchTerm = $("input.morphsearch-input").val().trim();
      console.log("Searching: "+searchTerm)
      if (searchTerm!=""){
        findImages(searchTerm.toLowerCase());
      }
    }
  );
  _findRoute.click(
    function(){
      getProgress();
      getResult(_fromImg, _toImg);
    }
  )

}

// Public functions
this.findImages = findImages;
this.getResult = getResult;
this.getProgress = getProgress;

// Start
_constructor();

}
