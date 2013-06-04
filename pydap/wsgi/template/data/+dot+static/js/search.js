$(document).ready(function(){
    $('<form style="float: right;"><input id="q" type="text" />&nbsp;<input id="submit" type="submit" value="search server" /></form>').prependTo('#main');
    $('<div id="results"></div>').insertAfter('#title');

    $('#q').focus();
    $(document).bind('keyup', '/', function() {
        $('#q').focus();
     });
    $(document).bind('keyup', 'esc', function() {
        $('#results').slideUp();
        $('#results').html(' ');
     });
    $('#submit').button();

    $('#submit').click(function() {
        $('#results').show();
        loadResults(1);  // load results for page 1
        return false;
    });
});

function loadResults(page) {
    $.getJSON(
        root + '?q=' + $('#q').val() + '&pw=' + page,
        function(data) {
            if (data.total > 0) {
                $('#results').html(
                    '<div class="message ui-state-highlight"><p>Found <strong>' + data.total + '</strong> dataset' + ((data.total > 1) ? 's' : '') + 
                    ' that match your search for <strong>' + $('#q').val() + '</strong>.</p></div>' + 
                    '<p>Showing results ' + (data.offset+1) + '&mdash;' + (data.offset+data.pagelen) + ':</p><table></table>'
                );
            } else {
                $('#results').html(
                    '<div class="message ui-state-error"><p>Found no results for your search for <strong>' + $('#q').val() + '</strong>.</p></div>'
                );
            }

            $('#results table').hide();
            $.each(data.results, function(index, result) {
                $('#results table').append(
                    '<tr class="ui-widget-content"><td>' + 
                    '<span class="ui-icon ui-icon-gear" style="display: inline-block"></span>' + 
                    '<a href="' + result.path + '">' + unescape(result.title) + '</a></td></tr>'
                );
            });

            if ((data.next) || (data.previous)) $('#results').append('<p id="nav"></p>');
            if (data.previous) $('<a href="#"><span class="ui-icon ui-icon-arrowthick-1-w" style="display: inline-block"></span>previous</a>').appendTo('#nav').click(function() { loadResults(page-1); });
            if ((data.next) && (data.previous)) $('#nav').append(' | ');
            if (data.next) $('<a href="#">next<span class="ui-icon ui-icon-arrowthick-1-e" style="display: inline-block"></span></a>').appendTo('#nav').click(function() { loadResults(page+1); });

            $('#results').append('<p class="footnote">Press &lt;ESC&gt; to clear this message.<span class="ui-icon ui-icon-arrowthick-1-n" style="display: inline-block"></span></p>');
            $('#results table').slideDown();
        }
    );
    return false;
}

// temporal/spatial search
