var myApp = angular.module('KnoWhere', ["ui.bootstrap"]);

myApp.controller('MainController', function MainController() {
  this.name = "KnoWhere";

/*
  this.total = function total(outCurr) {
    return this.convertCurrency(this.qty * this.cost, this.inCurr, outCurr);
  };
  this.convertCurrency = function convertCurrency(amount, inCurr, outCurr) {
    return amount * this.usdToForeignRates[outCurr] / this.usdToForeignRates[inCurr];
  };
  this.pay = function pay() {
    window.alert('Thanks!');
  };*/
});

/*** Define factories ***/


function addZ(n){return n<10 ? '0' + n : ''+n;}
function dateToStr(d, fmt){
  if(fmt == "ymd"){
    return d.getFullYear() + "-" + addZ(d.getMonth()+1) + "-"  + addZ(d.getDate());
  } else {
    return d.toDateString();
  }
}

/*** FORM ***/
myApp.service("shared", function(){
  var userData = undefined;
  var d = new Date();
  var start_date = d
  var end_date = d

  return {
    getStartDate: function() {return start_date;},
    getEndDate: function(){return end_date;},
    setStartDate: function(d){start_date = d;},
    setEndDate: function(d){end_date = d;}
  }
});

myApp.controller("FormController", function(shared, Users){
  this.selected_user = undefined;
  this.users = Users;
  d = new Date();
  this.today = dateToStr(d, "ymd")
  this.start_date = shared.getStartDate();
  this.end_date = shared.getEndDate();
  this.setStartDate = shared.setStartDate;
  this.setEndDate = shared.setEndDate;

 /* var handleGetUniqueUsers = function(data, status) {
    this.users = data;
  };
  Users.getUniqueUsers().success(handleGetUniqueUsers)*/
});

myApp.factory("Users", function($http){
  /*return {
    getUniqueUsers: function() {
      return $http.get("/getUniqueUsers");
    },
    getUserData: function(fname) {
      return $http.get("/getData")
    }
  };*/
  return ["Andrew", "Bill", "Emil", "Glen"];
});


myApp.factory("Dates", function(){
  return 0 //get min and max dates from the returned data;
});


/*** OVERVIEW ***/
myApp.controller("OverviewController", function($scope, shared){

  start_date = shared.getStartDate()
  end_date = shared.getEndDate()
  this.date_range = toDateRange(start_date, end_date);
  
  $scope.$watch(function(){
    return shared.getStartDate();
  }, function (newVal, oldVal, scope){
    if(newVal !== undefined){
      start_date = newVal;
    }
    scope.overview.date_range = toDateRange(start_date, end_date);
  });

  $scope.$watch(function(){
    return shared.getEndDate();
  }, function (newVal, oldVal, scope){
    if(newVal !== undefined){
      end_date = newVal;
    }
    scope.overview.date_range = toDateRange(start_date, end_date)
  });

  function toDateRange(start_date, end_date){
    if(start_date == end_date){
      date_range = dateToStr(end_date, "");
    } else {
      date_range = dateToStr(start_date, "") + " \u2013 " + dateToStr(end_date, "");
    }

    return date_range
  }

});