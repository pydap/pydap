$(document).ready(function(){
    // Activate accordion.
    $("#variables").accordion({
        active: false,
        collapsible: true
    });

    // Add more selections to filter sequences.
    var re = /(.*)\[(\d+)\]/;
    $('p.filter:last > select.var1').change(function() {
        if (this.value != '--') {
            var snippet = $(this.parentNode).clone(true);
            // Replace ids with unique ones.
            snippet.find('.var1,.op,.var2').each(function() {
                match = re.exec(this.id);
                base = match[1];
                counter = parseInt(match[2]) + 1;
                this.name = this.id = base + '[' + counter + ']';
            });
            snippet.insertAfter(this.parentNode);
            $(this).unbind('change');
        }
    });

    // Activate tabs.
    $("#tabs").tabs();

    // Add map.
    var map = new OpenLayers.Map('map');
    map.addControl( new OpenLayers.Control.LayerSwitcher({
            div: document.getElementById('layers'),
            roundedCorner: false
    }) );
    var wms = new OpenLayers.Layer.WMS( "OpenLayers WMS",
             "http://labs.metacarta.com/wms/vmap0", {layers: 'basic'},
             {wrapDateLine: true});
    map.addLayer(wms);
    map.zoomToMaxExtent();
    map.zoomIn();

    // Add layers.
    var location = document.location.href.split( /\?|#/ )[0];  // remove query-string and anchor
    var dataset = location.substr(0, location.length-5);

    var layers = [];
    /*var kml = new OpenLayers.Layer.GML("KML", dataset + ".kml", {
        format: OpenLayers.Format.KML,
        formatOptions: {
            extractStyles: true,
            extractAttributes: true
        }
    });
    layers.push(kml);*/

    $.ajax({
        type: "GET",
        url: dataset + ".wms?REQUEST=GetCapabilities",
        dataType: "xml",
        success: function(xml) {
            $(xml).find('Layer > Layer').each(function() {
                var name = $(this).find('Name').text();
                var title = $(this).find('Title').text();
                layer = new OpenLayers.Layer.WMS( title, dataset + ".wms",
                    {layers: name, TRANSPARENT: true},
                    {isBaseLayer: false}
                );
                layer.setOpacity(0.8);
                layer.setVisibility(false);
                layers.push(layer);
            });
            if (layers.length > 0) {
                map.addLayers(layers);
                $("#wms").prepend("<h2>Visualizing data</h2>");
            } else {
                $("#tabs").tabs('disable', 1);
                $("#wms").prepend("<h2>No qualifying data available</h2><p>Sorry, this dataset doesn't have any variables that can be represented as maps.</p>");
            }
        }
    });
});
