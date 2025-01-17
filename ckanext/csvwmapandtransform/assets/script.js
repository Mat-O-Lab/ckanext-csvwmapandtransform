ckan.module('csvwmapandtransform', function (jQuery) {
    return {
      options: {
        parameters: {
          html: {
            contentType: 'application/json', // change the content type to text/html
            dataType: 'json', // change the data type to html
            dataConverter: function (data) { return data; },
            language: 'json'
          }
        }
      },
      initialize: function () {
        var self = this;
        var p;
        p = this.options.parameters.html;
        console.log("Initialized csvwmapandtransform for element: ", this.el);
        const apiUrl = this.el.get(0).getAttribute("data-api-url"); // Fetch the API URL from the parent element
        if (!apiUrl) {
          console.error("No API URL specified for counter:", this.el);
          return;
        }
        var log_length;
        log_length = 0;
        var update = function () { // define the update function
          jQuery.ajax({
            url: apiUrl,
            type: 'GET',
            contentType: p.contentType,
            dataType: p.dataType,
            data: { get_param: 'value' },
            success: function (data) {
              const haslogs = 'logs' in data.status;
              const hasresults = data.status?.data?.files;
              if (hasresults || haslogs) {
                // console.log(self.el.find('button[name="delete"]'));
                self.el.find('button[name="delete"]').removeClass("invisible");
                self.el.find('div[name="status"]').removeClass("invisible");
              };
              // console.log(haslogs, hasresults);
              if (!haslogs) return;
              var length = Object.keys(data.status.logs).length;
              if (length) {
                if (length !== log_length) {
                  // self.el.html(JSON.stringify(data, null, 2)); // update the HTML if there are changes
                  var logs_div = $(self.el).find('ul[name="log"]');
                  jQuery.each(data.status.logs, function (key, value) {
                    if (key + 1 < log_length) return;
                    logs_div.append("<li class='item "
                      + value.class +
                      "'><i class='fa icon fa-"
                      + value.icon +
                      "'></i><div class='alert alert-"
                      + value.alertlevel +
                      " mb-0 mt-3' role='alert'>"
                      + value.message +
                      "</div><span class='date' title='timestamp'>"
                      + value.timestamp +
                      "</span></li>");
                    console.log("Appending log:", value);
                  });
                  console.log("csvwmapandtransform: status updated");
                  log_length = length;
                }
              } else {
                // console.log('no log changes');
              }
            },
            error: function (xhr, status, error) {
              console.log('Error:', error);
            },
            complete: function () {
              // call the update function recursively after a delay
              setTimeout(update, 2000);
            }
          });
        };
        update(); // call the update function immediately after initialization
      }
    };
  });